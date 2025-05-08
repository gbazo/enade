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
import parse
from parse_rest.connection import register
from parse_rest.datatypes import Object
from parse_rest.query import QueryResourceDoesNotExist

app = FastAPI(title="Sistema de Questionários ENADE")

# Configurações do Parse Server
APPLICATION_ID = os.environ.get("s7pKPlnBzfYSLKpV2MvxN6ahLQRreBVjRKGmXhaD")
REST_API_KEY = os.environ.get("s7pKPlnBzfYSLKpV2MvxN6ahLQRreBVjRKGmXhaD")

# Registrar com o Parse
register(APPLICATION_ID, REST_API_KEY)

# Definir classes do Parse
class ParseQuestion(Object):
    pass

class ParseQuestionnaire(Object):
    pass

class ParseResponse(Object):
    pass

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

# Funções CRUD usando Parse Server

def load_questions():
    """
    Carrega questões do Parse Server.
    Se não existirem, cria questões de exemplo.
    
    Returns:
        list: Lista de questões
    """
    try:
        # Buscar todas as questões do Parse Server
        questions_query = ParseQuestion.Query.all().order_by("number")
        parse_questions = list(questions_query)
        
        # Converter para o formato esperado pelo frontend
        questions = []
        for pq in parse_questions:
            question = {
                "id": pq.question_id,
                "number": pq.number,
                "text": pq.text,
                "type": pq.type,
                "category": pq.category,
                "options": json.loads(pq.options)
            }
            questions.append(question)
        
        # Se não houver questões, criar questões de exemplo
        if not questions:
            print("Nenhuma questão encontrada. Criando questões de exemplo...")
            questions = extract_questions_from_pdf()
            save_questions(questions)
        
        return questions
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
            try:
                pq = ParseQuestion.Query.get(question_id=question["id"])
                # Atualizar se existir
                pq.number = question["number"]
                pq.text = question["text"]
                pq.type = question["type"]
                pq.category = question["category"]
                pq.options = json.dumps(question["options"])
                pq.save()
            except QueryResourceDoesNotExist:
                # Criar nova questão
                pq = ParseQuestion(
                    question_id=question["id"],
                    number=question["number"],
                    text=question["text"],
                    type=question["type"],
                    category=question["category"],
                    options=json.dumps(question["options"])
                )
                pq.save()
        
        return True
    except Exception as e:
        print(f"Erro ao salvar questões: {e}")
        return False

def load_questionnaires():
    """
    Carrega todos os questionários do Parse Server
    """
    try:
        questionnaires_query = ParseQuestionnaire.Query.all()
        parse_questionnaires = list(questionnaires_query)
        
        # Converter para o formato esperado pelo frontend
        questionnaires = []
        for pq in parse_questionnaires:
            questionnaire = {
                "id": pq.questionnaire_id,
                "title": pq.title,
                "description": pq.description,
                "question_ids": json.loads(pq.question_ids),
                "created_at": pq.created_at.isoformat() if hasattr(pq, 'created_at') else datetime.now().isoformat()
            }
            questionnaires.append(questionnaire)
        
        return questionnaires
    except Exception as e:
        print(f"Erro ao carregar questionários: {e}")
        return []

def save_questionnaire(questionnaire_data):
    """
    Salva um questionário individual no Parse Server
    """
    try:
        # Verificar se o questionário já existe
        try:
            pq = ParseQuestionnaire.Query.get(questionnaire_id=questionnaire_data["id"])
            # Atualizar se existir
            pq.title = questionnaire_data["title"]
            pq.description = questionnaire_data["description"]
            pq.question_ids = json.dumps(questionnaire_data["question_ids"])
            pq.save()
        except QueryResourceDoesNotExist:
            # Criar novo questionário
            pq = ParseQuestionnaire(
                questionnaire_id=questionnaire_data["id"],
                title=questionnaire_data["title"],
                description=questionnaire_data["description"],
                question_ids=json.dumps(questionnaire_data["question_ids"]),
                created_at=datetime.now()
            )
            pq.save()
        
        return True
    except Exception as e:
        print(f"Erro ao salvar questionário: {e}")
        return False

def delete_questionnaire(questionnaire_id):
    """
    Remove um questionário do Parse Server
    """
    try:
        try:
            pq = ParseQuestionnaire.Query.get(questionnaire_id=questionnaire_id)
            pq.delete()
            return True
        except QueryResourceDoesNotExist:
            return False
    except Exception as e:
        print(f"Erro ao excluir questionário: {e}")
        return False

def load_responses():
    """
    Carrega todas as respostas do Parse Server
    """
    try:
        responses_query = ParseResponse.Query.all().descending("created_at")
        parse_responses = list(responses_query)
        
        # Converter para o formato esperado pelo frontend
        responses = []
        for pr in parse_responses:
            response = {
                "studentName": pr.studentName,
                "studentId": pr.studentId,
                "studentEmail": pr.studentEmail if hasattr(pr, 'studentEmail') else "",
                "questionnaire": pr.questionnaire,
                "submissionDate": pr.created_at.isoformat() if hasattr(pr, 'created_at') else datetime.now().isoformat(),
                "responses": json.loads(pr.responses)
            }
            responses.append(response)
        
        return responses
    except Exception as e:
        print(f"Erro ao carregar respostas: {e}")
        return []

def save_response(response_data):
    """
    Salva uma resposta de questionário no Parse Server
    """
    try:
        # Criar nova resposta
        pr = ParseResponse(
            studentName=response_data.get("studentName", ""),
            studentId=response_data.get("studentId", ""),
            studentEmail=response_data.get("studentEmail", ""),
            questionnaire=response_data.get("questionnaire", ""),
            responses=json.dumps(response_data.get("responses", []))
        )
        pr.save()
        
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
        # Verificar conexão com o Parse Server
        question_count = ParseQuestion.Query.all().count()
        questionnaire_count = ParseQuestionnaire.Query.all().count()
        response_count = ParseResponse.Query.all().count()
        
        return {
            "status": "online",
            "database": "Parse Server",
            "counts": {
                "questions": question_count,
                "questionnaires": questionnaire_count,
                "responses": response_count
            },
            "version": "1.0.0",
            "environment": "back4app"
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

@app.get("/api/questions/{question_id}", response_model=Question)
def get_question(question_id: int):
    try:
        pq = ParseQuestion.Query.get(question_id=question_id)
        
        # Converter para o formato esperado
        question = {
            "id": pq.question_id,
            "number": pq.number,
            "text": pq.text,
            "type": pq.type,
            "category": pq.category,
            "options": json.loads(pq.options)
        }
        
        return question
    except QueryResourceDoesNotExist:
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
        pq = ParseQuestionnaire.Query.get(questionnaire_id=questionnaire_id)
        
        # Converter para o formato esperado
        questionnaire = {
            "id": pq.questionnaire_id,
            "title": pq.title,
            "description": pq.description,
            "question_ids": json.loads(pq.question_ids),
            "created_at": pq.created_at.isoformat() if hasattr(pq, 'created_at') else datetime.now().isoformat()
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
    except QueryResourceDoesNotExist:
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
            last_questionnaire = list(ParseQuestionnaire.Query.all().order_by("-questionnaire_id").limit(1))
            new_id = 1 if not last_questionnaire else last_questionnaire[0].questionnaire_id + 1
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
        pq = ParseQuestionnaire(
            questionnaire_id=new_id,
            title=questionnaire.title,
            description=questionnaire.description,
            question_ids=json.dumps(valid_question_ids),
            created_at=datetime.now()
        )
        pq.save()
        
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
