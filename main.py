# Adicionando importações para MongoDB
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
import traceback
from datetime import datetime
from pymongo import MongoClient
import pymongo

app = FastAPI(title="Sistema de Questionários ENADE")

# Configurações para o MongoDB do Back4App
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("DB_NAME", "enade_app")

# Função para criar conexão com o MongoDB
def get_db_connection():
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    return db, client

# Função para fechar a conexão
def close_db_connection(client):
    if client:
        client.close()

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

# Diretório para armazenar dados - mantemos para compatibilidade e migração
DATA_DIR = "data"
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")
QUESTIONNAIRES_FILE = os.path.join(DATA_DIR, "questionnaires.json")
RESPONSES_FILE = os.path.join(DATA_DIR, "responses.json")

# Garantir que os diretórios existem para migração
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs("static", exist_ok=True)
except Exception as e:
    print(f"AVISO: Não foi possível criar diretórios: {e}")

# Inicializar o banco de dados MongoDB
def init_db():
    """
    Inicializa o MongoDB, criando índices necessários
    """
    try:
        db, client = get_db_connection()
        
        # Criar índices para coleções
        db.questions.create_index([("id", pymongo.ASCENDING)], unique=True)
        db.questionnaires.create_index([("id", pymongo.ASCENDING)], unique=True)
        db.questionnaires.create_index("title")
        
        print("Banco de dados MongoDB inicializado com sucesso")
        
        close_db_connection(client)
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados MongoDB: {e}")

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

# Função para migrar dados JSON para MongoDB
def migrate_data_from_json():
    """
    Migra dados de arquivos JSON para o MongoDB
    """
    print("Iniciando migração de dados JSON para MongoDB...")
    
    try:
        db, client = get_db_connection()
        
        # Verificar se já existem dados no banco
        if db.questions.count_documents({}) > 0 or db.questionnaires.count_documents({}) > 0:
            print("Dados já existem no banco, pulando migração")
            close_db_connection(client)
            return
        
        # Migrar questões
        if os.path.exists(QUESTIONS_FILE):
            try:
                with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
                    questions = json.load(f)
                
                if questions:
                    for question in questions:
                        db.questions.replace_one({"id": question["id"]}, question, upsert=True)
                    print(f"Migração de {len(questions)} questões concluída")
            except Exception as e:
                print(f"Erro ao migrar questões: {e}")
        
        # Migrar questionários
        if os.path.exists(QUESTIONNAIRES_FILE):
            try:
                with open(QUESTIONNAIRES_FILE, "r", encoding="utf-8") as f:
                    questionnaires = json.load(f)
                
                if questionnaires:
                    for questionnaire in questionnaires:
                        # Garantir que created_at seja uma string
                        if "created_at" in questionnaire and not isinstance(questionnaire["created_at"], str):
                            questionnaire["created_at"] = questionnaire["created_at"].isoformat()
                        
                        db.questionnaires.replace_one({"id": questionnaire["id"]}, questionnaire, upsert=True)
                    print(f"Migração de {len(questionnaires)} questionários concluída")
            except Exception as e:
                print(f"Erro ao migrar questionários: {e}")
        
        # Migrar respostas
        if os.path.exists(RESPONSES_FILE):
            try:
                with open(RESPONSES_FILE, "r", encoding="utf-8") as f:
                    responses = json.load(f)
                
                if responses:
                    db.responses.insert_many(responses)
                    print(f"Migração de {len(responses)} respostas concluída")
            except Exception as e:
                print(f"Erro ao migrar respostas: {e}")
        
        close_db_connection(client)
        print("Migração de dados JSON para MongoDB concluída")
    except Exception as e:
        print(f"Erro durante a migração de dados: {e}")

# Funções CRUD substituídas para usar MongoDB

def load_questions():
    """
    Carrega questões do MongoDB.
    Se não existirem, cria questões de exemplo.
    
    Returns:
        list: Lista de questões
    """
    try:
        db, client = get_db_connection()
        # Buscar todas as questões, ordenadas por número
        questions = list(db.questions.find({}, {'_id': 0}).sort("number", 1))
        close_db_connection(client)
        
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
    Salva múltiplas questões no MongoDB
    """
    try:
        db, client = get_db_connection()
        
        for question in questions:
            # Inserir ou atualizar questão
            db.questions.replace_one({"id": question["id"]}, question, upsert=True)
        
        close_db_connection(client)
        return True
    except Exception as e:
        print(f"Erro ao salvar questões: {e}")
        return False

def load_questionnaires():
    """
    Carrega todos os questionários do MongoDB
    """
    try:
        db, client = get_db_connection()
        # Excluir o campo _id na resposta
        questionnaires = list(db.questionnaires.find({}, {'_id': 0}))
        close_db_connection(client)
        return questionnaires
    except Exception as e:
        print(f"Erro ao carregar questionários: {e}")
        return []

def save_questionnaires(questionnaires):
    """
    Salva a lista completa de questionários no MongoDB
    (Para compatibilidade com o código original)
    """
    try:
        db, client = get_db_connection()
        
        # Limpar coleção atual
        db.questionnaires.delete_many({})
        
        # Inserir todos os questionários
        if questionnaires:
            db.questionnaires.insert_many(questionnaires)
        
        close_db_connection(client)
        return True
    except Exception as e:
        print(f"Erro ao salvar questionários: {e}")
        return False

def save_questionnaire(questionnaire_data):
    """
    Salva um questionário individual no MongoDB
    """
    try:
        db, client = get_db_connection()
        
        # Inserir ou atualizar questionário
        result = db.questionnaires.replace_one(
            {"id": questionnaire_data["id"]}, 
            questionnaire_data, 
            upsert=True
        )
        
        close_db_connection(client)
        return True
    except Exception as e:
        print(f"Erro ao salvar questionário: {e}")
        return False

def load_responses():
    """
    Carrega todas as respostas do MongoDB
    """
    try:
        db, client = get_db_connection()
        
        # Excluir o campo _id na resposta
        responses = list(db.responses.find({}, {'_id': 0}).sort("submissionDate", -1))
        
        close_db_connection(client)
        return responses
    except Exception as e:
        print(f"Erro ao carregar respostas: {e}")
        return []

def save_response(response_data):
    """
    Salva uma resposta de questionário no MongoDB
    """
    try:
        db, client = get_db_connection()
        
        # Garantir que submissionDate seja uma string
        if "submissionDate" in response_data and not isinstance(response_data["submissionDate"], str):
            response_data["submissionDate"] = response_data["submissionDate"].isoformat()
        
        # Inserir a resposta
        db.responses.insert_one(response_data)
        
        close_db_connection(client)
        return True
    except Exception as e:
        print(f"Erro ao salvar resposta: {e}")
        return False

# Eventos para gerenciar o banco de dados
@app.on_event("startup")
async def startup_db_client():
    """
    Inicializa o banco de dados na inicialização da aplicação.
    """
    print("Inicializando banco de dados MongoDB...")
    init_db()
    
    # Verificar se já existem dados no banco
    db, client = get_db_connection()
    
    question_count = db.questions.count_documents({})
    questionnaire_count = db.questionnaires.count_documents({})
    response_count = db.responses.count_documents({})
    
    print(f"Banco de dados contém: {question_count} questões, {questionnaire_count} questionários, {response_count} respostas")
    
    # Se não houver dados, migrar dos arquivos JSON (se existirem)
    if question_count == 0 and questionnaire_count == 0 and response_count == 0:
        print("Banco de dados vazio, verificando arquivos JSON para migração...")
        close_db_connection(client)
        migrate_data_from_json()
    else:
        close_db_connection(client)
    
    print("Inicialização do banco de dados concluída")

@app.on_event("shutdown")
async def shutdown_db_client():
    """
    Finaliza conexões com o banco de dados quando a aplicação é encerrada.
    """
    print("Finalizando conexões com o banco de dados...")
    # Não é necessário fazer nada específico aqui, pois fechamos as conexões após cada operação
    print("Conexões com o banco de dados finalizadas")

# Montar diretório estático - deve vir ANTES das rotas da API para evitar conflitos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Rotas da API
@app.get("/api")
def read_root():
    return {"message": "Sistema de Questionários ENADE API"}

@app.get("/api/test")
async def test_api():
    return {"status": "success", "message": "API está online"}

# Endpoint de status específico para o Back4App
@app.get("/api/status")
def get_status():
    """
    Endpoint de status para verificar se a API está funcionando
    """
    try:
        # Verificar conexão com o MongoDB
        db, client = get_db_connection()
        db_status = "conectado"
        
        # Contar itens em cada coleção
        question_count = db.questions.count_documents({})
        questionnaire_count = db.questionnaires.count_documents({})
        response_count = db.responses.count_documents({})
        
        close_db_connection(client)
        
        return {
            "status": "online",
            "database": db_status,
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
        db, client = get_db_connection()
        question = db.questions.find_one({"id": question_id}, {'_id': 0})
        close_db_connection(client)
        
        if question:
            return question
    except Exception as e:
        print(f"Erro ao buscar questão: {e}")
    
    raise HTTPException(status_code=404, detail="Questão não encontrada")

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
        db, client = get_db_connection()
        questionnaire = db.questionnaires.find_one({"id": questionnaire_id}, {'_id': 0})
        close_db_connection(client)
        
        if not questionnaire:
            raise HTTPException(status_code=404, detail="Questionário não encontrado")
        
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
    except Exception as e:
        print(f"Erro ao buscar questionário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar questionário")

@app.post("/api/questionnaires", response_model=Questionnaire)
def create_questionnaire(questionnaire: QuestionnaireCreate):
    try:
        db, client = get_db_connection()
        
        # Gerar ID para o novo questionário
        last_questionnaire = db.questionnaires.find_one(sort=[("id", -1)])
        new_id = 1 if not last_questionnaire else last_questionnaire["id"] + 1
        
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
        
        # Salvar no MongoDB
        db.questionnaires.insert_one(new_questionnaire)
        close_db_connection(client)
        
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
def delete_questionnaire(questionnaire_id: int):
    try:
        db, client = get_db_connection()
        
        # Verificar se o questionário existe
        questionnaire = db.questionnaires.find_one({"id": questionnaire_id})
        if not questionnaire:
            close_db_connection(client)
            raise HTTPException(status_code=404, detail="Questionário não encontrado")
        
        # Excluir o questionário
        db.questionnaires.delete_one({"id": questionnaire_id})
        close_db_connection(client)
        
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
            raise HTTPException(
                status_code=500,
                detail="Erro ao salvar resposta"
            )
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
    # Obter porta do ambiente ou usar 8000 como padrão - Back4App usa a variável PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
