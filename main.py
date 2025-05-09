from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import traceback
from datetime import datetime
import requests

app = FastAPI(title="Sistema de Questionários ENADE")

# Configurações do Parse Server
PARSE_APP_ID = os.environ.get("PARSE_APP_ID", "s7pKPlnBzfYSLKpV2MvxN6ahLQRreBVjRKGmXhaD")
PARSE_REST_API_KEY = os.environ.get("PARSE_REST_API_KEY", "BsRIEaRzKtWkIdz70UrddtHaFsHJdLkYHszT4O6Y")
PARSE_SERVER_URL = os.environ.get("PARSE_SERVER_URL", "https://parseapi.back4app.com")

# Headers para requisições ao Parse Server
PARSE_HEADERS = {
    "X-Parse-Application-Id": PARSE_APP_ID,
    "X-Parse-REST-API-Key": PARSE_REST_API_KEY,
    "Content-Type": "application/json"
}

# Middleware para tratar exceções e imprimir erros detalhados
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"ERRO: {str(e)}")
        print(error_detail)
        return JSONResponse(
            status_code=500,
            content={"message": f"Erro interno: {str(e)}"}
        )

# Configuração CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de dados
class QuestionOption(BaseModel):
    label: str
    text: str

class Question(BaseModel):
    id: int
    number: int
    text: str
    type: str
    category: str
    options: List[QuestionOption]

class QuestionnaireBase(BaseModel):
    title: str
    description: Optional[str] = None

class QuestionnaireCreate(QuestionnaireBase):
    questions: List[int]  # Lista de IDs de questões

class Questionnaire(QuestionnaireBase):
    id: int
    questions: List[Question]
    created_at: str

# Diretório para armazenar arquivos estáticos
os.makedirs("static", exist_ok=True)

# Verificar se existe pelo menos um arquivo HTML na pasta static
index_path = os.path.join("static", "index.html")
if not os.path.exists(index_path):
    print("AVISO: index.html não encontrado na pasta static.")

# Função para extrair questões do PDF do ENADE
def extract_questions_from_pdf(existing_questions=None):
    """
    Extrai questões do PDF, preservando questões existentes.
    
    Args:
        existing_questions (list, optional): Lista de questões existentes
    
    Returns:
        list: Lista atualizada de questões
    """
    # Se não houver questões existentes, iniciar com lista vazia
    questions = existing_questions or []
    
    # Verificar se já existem questões com IDs específicos para evitar duplicatas
    existing_ids = {q.get('id', 0) for q in questions}
    
    # Função auxiliar para adicionar questão se ID não existir
    def add_question_if_not_exists(question):
        if question['id'] not in existing_ids:
            questions.append(question)
            existing_ids.add(question['id'])
    
    # Questões de dados pessoais
    default_personal_questions = []
    
    # Adicionar questões padrão se não existirem
    for q in default_personal_questions:
        add_question_if_not_exists(q)
    
    # Adicionar questões de exemplo para completar o conjunto
    if len(questions) < 20:
        for i in range(len(questions) + 1, 21):
            category = ""
            question_type = ""
            
            if i <= 10:
                category = "dados-pessoais"
                question_type = "multiple-choice"
            elif i <= 19:
                category = "formacao"
                question_type = "multiple-choice"
            else:
                category = "academico"
                question_type = "likert"
            
            options = []
            if question_type == "multiple-choice":
                options = [
                    {"label": "A", "text": f"Opção A para questão {i}"},
                    {"label": "B", "text": f"Opção B para questão {i}"},
                    {"label": "C", "text": f"Opção C para questão {i}"},
                    {"label": "D", "text": f"Opção D para questão {i}"}
                ]
            else:  # likert
                options = [
                    {"label": "1", "text": "Discordo totalmente"},
                    {"label": "2", "text": ""},
                    {"label": "3", "text": ""},
                    {"label": "4", "text": ""},
                    {"label": "5", "text": ""},
                    {"label": "6", "text": "Concordo totalmente"},
                    {"label": "N", "text": "Não sei responder"},
                    {"label": "NA", "text": "Não se aplica"}
                ]
            
            add_question_if_not_exists({
                "id": i,
                "number": i,
                "text": f"Questão exemplo {i}: {['Dados pessoais', 'Formação acadêmica', 'Avaliação'][i % 3]}",
                "type": question_type,
                "category": category,
                "options": options
            })
    
    # Adicionar questões de licenciatura
    for i in range(50, 55):
        add_question_if_not_exists({
            "id": i,
            "number": i,
            "text": f"Competência {i-49}: Habilidade para aplicar conhecimentos na prática",
            "type": "likert",
            "category": "licenciatura",
            "options": [
                {"label": "1", "text": "Discordo totalmente"},
                {"label": "2", "text": ""},
                {"label": "3", "text": ""},
                {"label": "4", "text": ""},
                {"label": "5", "text": ""},
                {"label": "6", "text": "Concordo totalmente"},
                {"label": "N", "text": "Não sei responder"},
                {"label": "NA", "text": "Não se aplica"}
            ]
        })
    
    return questions

# Funções CRUD usando Parse REST API

def load_questions():
    """
    Carrega questões do Parse Server.
    Se não existirem, cria questões de exemplo.
    
    Returns:
        list: Lista de questões
    """
    try:
        # Buscar todas as questões do Parse Server
        url = f"{PARSE_SERVER_URL}/classes/Question"
        params = {
            "order": "number",
            "limit": 1000  # Ajustar conforme necessário
        }
        
        response = requests.get(url, headers=PARSE_HEADERS, params=params)
        
        if response.status_code == 200:
            result = response.json()
            
            # Converter para o formato esperado pelo frontend
            questions = []
            for item in result.get("results", []):
                question = {
                    "id": item.get("questionId"),
                    "number": item.get("number"),
                    "text": item.get("text"),
                    "type": item.get("type"),
                    "category": item.get("category"),
                    "options": item.get("options", [])
                }
                questions.append(question)
            
            # Se não houver questões, criar questões de exemplo
            if not questions:
                print("Nenhuma questão encontrada. Criando questões de exemplo...")
                questions = extract_questions_from_pdf()
                save_questions(questions)
            
            return questions
        else:
            print(f"Erro ao carregar questões: {response.status_code} - {response.text}")
            return extract_questions_from_pdf()
    except Exception as e:
        print(f"Erro ao carregar questões: {e}")
        # Em caso de erro, criar questões de exemplo
        return extract_questions_from_pdf()

def save_questions(questions):
    """
    Salva múltiplas questões no Parse Server
    """
    try:
        for question in questions:
            # Verificar se a questão já existe
            query_url = f"{PARSE_SERVER_URL}/classes/Question"
            params = {
                "where": json.dumps({"questionId": question["id"]})
            }
            
            response = requests.get(query_url, headers=PARSE_HEADERS, params=params)
            
            if response.status_code == 200 and len(response.json().get("results", [])) > 0:
                # Atualizar questão existente
                object_id = response.json()["results"][0]["objectId"]
                update_url = f"{PARSE_SERVER_URL}/classes/Question/{object_id}"
                
                update_data = {
                    "number": question["number"],
                    "text": question["text"],
                    "type": question["type"],
                    "category": question["category"],
                    "options": question["options"]
                }
                
                update_response = requests.put(update_url, headers=PARSE_HEADERS, data=json.dumps(update_data))
                
                if update_response.status_code != 200:
                    print(f"Erro ao atualizar questão: {update_response.status_code} - {update_response.text}")
            else:
                # Criar nova questão
                create_url = f"{PARSE_SERVER_URL}/classes/Question"
                
                create_data = {
                    "questionId": question["id"],
                    "number": question["number"],
                    "text": question["text"],
                    "type": question["type"],
                    "category": question["category"],
                    "options": question["options"]
                }
                
                create_response = requests.post(create_url, headers=PARSE_HEADERS, data=json.dumps(create_data))
                
                if create_response.status_code != 201:
                    print(f"Erro ao criar questão: {create_response.status_code} - {create_response.text}")
        
        return True
    except Exception as e:
        print(f"Erro ao salvar questões: {e}")
        return False

def load_questionnaires():
    """
    Carrega todos os questionários do Parse Server
    """
    try:
        url = f"{PARSE_SERVER_URL}/classes/Questionnaire"
        response = requests.get(url, headers=PARSE_HEADERS)
        
        if response.status_code == 200:
            result = response.json()
            
            # Converter para o formato esperado pelo frontend
            questionnaires = []
            for item in result.get("results", []):
                questionnaire = {
                    "id": item.get("questionnaireId"),
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "question_ids": item.get("questionIds", []),
                    "created_at": item.get("createdAt", datetime.now().isoformat())
                }
                questionnaires.append(questionnaire)
            
            return questionnaires
        else:
            print(f"Erro ao carregar questionários: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Erro ao carregar questionários: {e}")
        return []

def save_questionnaire(questionnaire_data):
    """
    Salva um questionário individual no Parse Server
    """
    try:
        # Verificar se o questionário já existe
        query_url = f"{PARSE_SERVER_URL}/classes/Questionnaire"
        params = {
            "where": json.dumps({"questionnaireId": questionnaire_data["id"]})
        }
        
        response = requests.get(query_url, headers=PARSE_HEADERS, params=params)
        
        if response.status_code == 200 and len(response.json().get("results", [])) > 0:
            # Atualizar questionário existente
            object_id = response.json()["results"][0]["objectId"]
            update_url = f"{PARSE_SERVER_URL}/classes/Questionnaire/{object_id}"
            
            update_data = {
                "title": questionnaire_data["title"],
                "description": questionnaire_data["description"],
                "questionIds": questionnaire_data["question_ids"]
            }
            
            update_response = requests.put(update_url, headers=PARSE_HEADERS, data=json.dumps(update_data))
            
            if update_response.status_code != 200:
                print(f"Erro ao atualizar questionário: {update_response.status_code} - {update_response.text}")
                return False
        else:
            # Criar novo questionário
            create_url = f"{PARSE_SERVER_URL}/classes/Questionnaire"
            
            create_data = {
                "questionnaireId": questionnaire_data["id"],
                "title": questionnaire_data["title"],
                "description": questionnaire_data["description"],
                "questionIds": questionnaire_data["question_ids"],
                "createdAt": questionnaire_data.get("created_at", datetime.now().isoformat())
            }
            
            create_response = requests.post(create_url, headers=PARSE_HEADERS, data=json.dumps(create_data))
            
            if create_response.status_code != 201:
                print(f"Erro ao criar questionário: {create_response.status_code} - {create_response.text}")
                return False
        
        return True
    except Exception as e:
        print(f"Erro ao salvar questionário: {e}")
        return False

def delete_questionnaire(questionnaire_id):
    """
    Remove um questionário do Parse Server
    """
    try:
        # Encontrar o objectId do questionário
        query_url = f"{PARSE_SERVER_URL}/classes/Questionnaire"
        params = {
            "where": json.dumps({"questionnaireId": questionnaire_id})
        }
        
        response = requests.get(query_url, headers=PARSE_HEADERS, params=params)
        
        if response.status_code == 200 and len(response.json().get("results", [])) > 0:
            object_id = response.json()["results"][0]["objectId"]
            
            # Excluir o questionário
            delete_url = f"{PARSE_SERVER_URL}/classes/Questionnaire/{object_id}"
            delete_response = requests.delete(delete_url, headers=PARSE_HEADERS)
            
            if delete_response.status_code != 200:
                print(f"Erro ao excluir questionário: {delete_response.status_code} - {delete_response.text}")
                return False
            
            return True
        else:
            print("Questionário não encontrado")
            return False
    except Exception as e:
        print(f"Erro ao excluir questionário: {e}")
        return False

def load_responses():
    """
    Carrega todas as respostas do Parse Server
    """
    try:
        url = f"{PARSE_SERVER_URL}/classes/Response"
        params = {
            "order": "-createdAt",
            "limit": 1000  # Ajustar conforme necessário
        }
        
        response = requests.get(url, headers=PARSE_HEADERS, params=params)
        
        if response.status_code == 200:
            result = response.json()
            
            # Converter para o formato esperado pelo frontend
            responses = []
            for item in result.get("results", []):
                resp = {
                    "studentName": item.get("studentName", ""),
                    "studentId": item.get("studentId", ""),
                    "studentEmail": item.get("studentEmail", ""),
                    "questionnaire": item.get("questionnaire", ""),
                    "submissionDate": item.get("createdAt", datetime.now().isoformat()),
                    "responses": item.get("responses", [])
                }
                responses.append(resp)
            
            return responses
        else:
            print(f"Erro ao carregar respostas: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Erro ao carregar respostas: {e}")
        return []

def save_response(response_data):
    """
    Salva uma resposta de questionário no Parse Server
    """
    try:
        # Criar nova resposta
        url = f"{PARSE_SERVER_URL}/classes/Response"
        
        data = {
            "studentName": response_data.get("studentName", ""),
            "studentId": response_data.get("studentId", ""),
            "studentEmail": response_data.get("studentEmail", ""),
            "questionnaire": response_data.get("questionnaire", ""),
            "responses": response_data.get("responses", [])
        }
        
        response = requests.post(url, headers=PARSE_HEADERS, data=json.dumps(data))
        
        if response.status_code != 201:
            print(f"Erro ao salvar resposta: {response.status_code} - {response.text}")
            return False
        
        return True
    except Exception as e:
        print(f"Erro ao salvar resposta: {e}")
        return False

# Montar diretório estático - deve vir ANTES das rotas da API para evitar conflitos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Rotas da API
@app.get("/api")
def read_root():
    return {"message": "Sistema de Questionários ENADE API"}

@app.get("/api/test")
async def test_api():
    return {"status": "success", "message": "API está online"}

# Endpoint de status específico
@app.get("/api/status")
def get_status():
    """
    Endpoint de status para verificar se a API está funcionando
    """
    try:
        # Verificar se as credenciais do Parse Server estão configuradas
        if not PARSE_APP_ID or not PARSE_REST_API_KEY:
            return {
                "status": "warning",
                "message": "Parse Server credentials not configured",
                "environment": "back4app"
            }
        
        # Tentar fazer uma requisição simples ao Parse Server
        test_url = f"{PARSE_SERVER_URL}/classes/Question"
        params = {"limit": 1}
        
        response = requests.get(test_url, headers=PARSE_HEADERS, params=params)
        
        if response.status_code == 200:
            # Contar itens em cada coleção
            questions_response = requests.get(f"{PARSE_SERVER_URL}/classes/Question", headers=PARSE_HEADERS, params={"count": 1, "limit": 0})
            questionnaires_response = requests.get(f"{PARSE_SERVER_URL}/classes/Questionnaire", headers=PARSE_HEADERS, params={"count": 1, "limit": 0})
            responses_response = requests.get(f"{PARSE_SERVER_URL}/classes/Response", headers=PARSE_HEADERS, params={"count": 1, "limit": 0})
            
            return {
                "status": "online",
                "database": "Parse Server",
                "counts": {
                    "questions": questions_response.json().get("count", 0) if questions_response.status_code == 200 else "error",
                    "questionnaires": questionnaires_response.json().get("count", 0) if questionnaires_response.status_code == 200 else "error",
                    "responses": responses_response.json().get("count", 0) if responses_response.status_code == 200 else "error"
                },
                "version": "1.0.0",
                "environment": "back4app",
                "parse_app_id": PARSE_APP_ID[:4] + "..." if PARSE_APP_ID else "not set"
            }
        else:
            return {
                "status": "error",
                "message": f"Parse Server connection failed with status {response.status_code}",
                "error": response.text[:100] + "..." if len(response.text) > 100 else response.text
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Rota para servir o arquivo de questões em JSON diretamente
@app.get("/questions.json")
def get_questions_json():
    return load_questions()

@app.get("/api/questions", response_model=List[Question])
def get_questions():
    return load_questions()

@app.get("/api/migrate-questions")
def migrate_questions_endpoint():
    try:
        # Verificar quais questões já existem no Parse Server
        existing_url = f"{PARSE_SERVER_URL}/classes/Question"
        params = {"limit": 1000}
        response = requests.get(existing_url, headers=PARSE_HEADERS, params=params)
        
        existing_ids = set()
        if response.status_code == 200:
            for item in response.json().get("results", []):
                existing_ids.add(item.get("questionId"))
        
        print(f"Encontradas {len(existing_ids)} questões já existentes no Parse Server")
        
        # Carregar todas as questões do arquivo JSON
        if os.path.exists(QUESTIONS_FILE):
            with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
                all_questions = json.load(f)
            
            print(f"Carregadas {len(all_questions)} questões do arquivo JSON")
            
            # Identificar questões faltantes
            missing_questions = [q for q in all_questions if q["id"] not in existing_ids]
            print(f"Identificadas {len(missing_questions)} questões faltantes")
            
            # Migrar cada questão faltante
            migrated_count = 0
            for question in missing_questions:
                try:
                    # Preparar dados para o Parse Server
                    question_data = {
                        "questionId": question["id"],
                        "number": question["number"],
                        "text": question["text"],
                        "type": question["type"],
                        "category": question["category"],
                        "options": question["options"]
                    }
                    
                    # Criar a questão no Parse Server
                    create_url = f"{PARSE_SERVER_URL}/classes/Question"
                    create_response = requests.post(create_url, headers=PARSE_HEADERS, data=json.dumps(question_data))
                    
                    if create_response.status_code == 201:
                        migrated_count += 1
                    else:
                        print(f"Erro ao migrar questão {question['id']}: {create_response.status_code} - {create_response.text}")
                except Exception as e:
                    print(f"Erro ao processar questão {question['id']}: {e}")
            
            # Retornar resultados
            return {
                "status": "success",
                "total_in_json": len(all_questions),
                "existing_in_parse": len(existing_ids),
                "missing_identified": len(missing_questions),
                "successfully_migrated": migrated_count,
                "final_total": len(existing_ids) + migrated_count
            }
        else:
            return {
                "status": "error",
                "message": f"Arquivo JSON não encontrado: {QUESTIONS_FILE}"
            }
    except Exception as e:
        print(f"Erro na migração: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/questions/{question_id}", response_model=Question)
def get_question(question_id: int):
    try:
        query_url = f"{PARSE_SERVER_URL}/classes/Question"
        params = {
            "where": json.dumps({"questionId": question_id})
        }
        
        response = requests.get(query_url, headers=PARSE_HEADERS, params=params)
        
        if response.status_code == 200 and len(response.json().get("results", [])) > 0:
            item = response.json()["results"][0]
            
            question = {
                "id": item.get("questionId"),
                "number": item.get("number"),
                "text": item.get("text"),
                "type": item.get("type"),
                "category": item.get("category"),
                "options": item.get("options", [])
            }
            
            return question
        else:
            raise HTTPException(status_code=404, detail="Questão não encontrada")
    except Exception as e:
        print(f"Erro ao buscar questão: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar questão")

@app.get("/api/questionnaires", response_model=List[Questionnaire])
def get_questionnaires():
    questionnaires = load_questionnaires()
    
    # Expandir as questões em cada questionário
    questions = load_questions()
    questions_dict = {q["id"]: q for q in questions}
    
    for q in questionnaires:
        expanded_questions = []
        for qid in q.get("question_ids", []):
            if qid in questions_dict:
                expanded_questions.append(questions_dict[qid])
        q["questions"] = expanded_questions
        # Remover a lista de IDs após expandir
        if "question_ids" in q:
            del q["question_ids"]
    
    return questionnaires

@app.get("/api/questionnaires/{questionnaire_id}", response_model=Questionnaire)
def get_questionnaire(questionnaire_id: int):
    try:
        query_url = f"{PARSE_SERVER_URL}/classes/Questionnaire"
        params = {
            "where": json.dumps({"questionnaireId": questionnaire_id})
        }
        
        response = requests.get(query_url, headers=PARSE_HEADERS, params=params)
        
        if response.status_code == 200 and len(response.json().get("results", [])) > 0:
            item = response.json()["results"][0]
            
            questionnaire = {
                "id": item.get("questionnaireId"),
                "title": item.get("title"),
                "description": item.get("description"),
                "question_ids": item.get("questionIds", []),
                "created_at": item.get("createdAt", datetime.now().isoformat())
            }
            
            # Expandir as questões
            questions = load_questions()
            questions_dict = {q["id"]: q for q in questions}
            
            expanded_questions = []
            for qid in questionnaire.get("question_ids", []):
                if qid in questions_dict:
                    expanded_questions.append(questions_dict[qid])
            
            questionnaire["questions"] = expanded_questions
            
            # Remover a lista de IDs após expandir
            if "question_ids" in questionnaire:
                del questionnaire["question_ids"]
            
            return questionnaire
        else:
            raise HTTPException(status_code=404, detail="Questionário não encontrado")
    except Exception as e:
        print(f"Erro ao buscar questionário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar questionário")

@app.post("/api/questionnaires", response_model=Questionnaire)
def create_questionnaire(questionnaire: QuestionnaireCreate):
    try:
        # Gerar ID para o novo questionário
        try:
            # Buscar o maior ID existente
            query_url = f"{PARSE_SERVER_URL}/classes/Questionnaire"
            params = {
                "order": "-questionnaireId",
                "limit": 1
            }
            
            response = requests.get(query_url, headers=PARSE_HEADERS, params=params)
            
            if response.status_code == 200 and len(response.json().get("results", [])) > 0:
                new_id = response.json()["results"][0].get("questionnaireId", 0) + 1
            else:
                new_id = 1
        except Exception:
            new_id = 1
        
        # Verificar se as questões existem
        questions = load_questions()
        questions_dict = {q["id"]: q for q in questions}
        
        valid_question_ids = []
        for qid in questionnaire.questions:
            if qid in questions_dict:
                valid_question_ids.append(qid)
        
        # Criar o novo questionário
        new_questionnaire = {
            "id": new_id,
            "title": questionnaire.title,
            "description": questionnaire.description,
            "question_ids": valid_question_ids,
            "created_at": datetime.now().isoformat()
        }
        
        # Salvar no Parse Server
        save_questionnaire(new_questionnaire)
        
        # Expandir as questões para o retorno
        expanded_questions = [questions_dict[qid] for qid in valid_question_ids]
        
        return {
            "id": new_id,
            "title": questionnaire.title,
            "description": questionnaire.description,
            "questions": expanded_questions,
            "created_at": new_questionnaire["created_at"]
        }
    except Exception as e:
        print(f"Erro ao criar questionário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar questionário")

@app.delete("/api/questionnaires/{questionnaire_id}", response_model=dict)
def delete_questionnaire_endpoint(questionnaire_id: int):
    try:
        success = delete_questionnaire(questionnaire_id)
        if not success:
            raise HTTPException(status_code=404, detail="Questionário não encontrado")
        
        return {"message": "Questionário removido com sucesso"}
    except Exception as e:
        print(f"Erro ao excluir questionário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao excluir questionário")

# Rota para servir arquivos estáticos específicos
@app.get("/styles.css")
async def serve_css():
    css_path = os.path.join("static", "styles.css")
    if not os.path.exists(css_path):
        # Criar um CSS básico se não existir
        with open(css_path, "w", encoding="utf-8") as f:
            f.write("""body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
}
header {
    background-color: #2c3e50;
    color: white;
    padding: 1rem;
    text-align: center;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}
""")
    return FileResponse(css_path, media_type="text/css")

@app.get("/script.js")
async def serve_js():
    js_path = os.path.join("static", "script.js")
    if not os.path.exists(js_path):
        # Criar um JS básico se não existir
        with open(js_path, "w", encoding="utf-8") as f:
            f.write("""document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema de Questionários ENADE carregado!');
});
""")
    return FileResponse(js_path, media_type="application/javascript")

@app.get("/api/responses")
def get_all_responses():
    return load_responses()

@app.post("/api/responses")
async def receive_response(request: Request):
    try:
        data = await request.json()
        success = save_response(data)
        if not success:
            raise HTTPException(status_code=500, detail="Erro ao salvar resposta")
        return {"message": "Resposta recebida com sucesso!"}
    except Exception as e:
        print("Erro ao salvar resposta:", e)
        raise HTTPException(status_code=400, detail="Erro ao processar os dados.")

# Rota para servir o frontend (SPA)
@app.get("/{path:path}")
async def serve_spa(path: str):
    # Verificar se é um arquivo que existe na pasta static
    file_path = os.path.join("static", path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Caso contrário, retorna o index.html (SPA)
    return FileResponse(os.path.join("static", "index.html"))

# Rota principal
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join("static", "index.html"))

# ============================
# INÍCIO DO SERVIDOR
# ============================

if __name__ == "__main__":
    import uvicorn
    # Obter porta do ambiente ou usar 8000 como padrão
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
