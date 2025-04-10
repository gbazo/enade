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

app = FastAPI(title="Sistema de Questionários ENADE")

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

# Diretório para armazenar dados
DATA_DIR = "data"
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")
QUESTIONNAIRES_FILE = os.path.join(DATA_DIR, "questionnaires.json")

# Garantir que os diretórios existem
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# Verificar se existe pelo menos um arquivo HTML na pasta static
index_path = os.path.join("static", "index.html")
if not os.path.exists(index_path):
    print("AVISO: index.html não encontrado na pasta static.")

# Função para carregar questões
def load_questions():
    if not os.path.exists(QUESTIONS_FILE):
        # Criar arquivo de questões se não existir
        with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(extract_questions_from_pdf(), f, ensure_ascii=False, indent=2)
    
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Função para carregar questionários
def load_questionnaires():
    if not os.path.exists(QUESTIONNAIRES_FILE):
        with open(QUESTIONNAIRES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    
    with open(QUESTIONNAIRES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Função para salvar questionários
def save_questionnaires(questionnaires):
    with open(QUESTIONNAIRES_FILE, "w", encoding="utf-8") as f:
        json.dump(questionnaires, f, ensure_ascii=False, indent=2)

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

def load_questions():
    """
    Carrega questões, criando o arquivo se não existir.
    Preserva questões existentes.
    
    Returns:
        list: Lista de questões
    """
    if not os.path.exists(QUESTIONS_FILE):
        # Se o arquivo não existe, criar com questões de exemplo
        questions = extract_questions_from_pdf()
        with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        return questions
    
    # Ler questões existentes
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        existing_questions = json.load(f)
    
    # Verificar se precisa adicionar mais questões
    if len(existing_questions) < 20:
        # Adicionar questões de exemplo mantendo as existentes
        updated_questions = extract_questions_from_pdf(existing_questions)
        
        # Salvar questões atualizadas
        with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_questions, f, ensure_ascii=False, indent=2)
        
        return updated_questions
    
    return existing_questions

def get_questions_json():
    """
    Obtém questões em formato JSON.
    Preserva questões existentes.
    
    Returns:
        list: Lista de questões
    """
    # Carregar ou criar o arquivo de questões
    if not os.path.exists(QUESTIONS_FILE):
        questions = extract_questions_from_pdf()
        with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        return questions
    
    # Ler questões existentes
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        existing_questions = json.load(f)
    
    # Verificar se precisa adicionar mais questões
    if len(existing_questions) < 20:
        updated_questions = extract_questions_from_pdf(existing_questions)
        
        # Salvar questões atualizadas
        with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_questions, f, ensure_ascii=False, indent=2)
        
        return updated_questions
    
    return existing_questions

# Montar diretório estático - deve vir ANTES das rotas da API para evitar conflitos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Rotas da API
@app.get("/api")
def read_root():
    return {"message": "Sistema de Questionários ENADE API"}

# Rota para servir o arquivo de questões em JSON diretamente
@app.get("/questions.json")
def get_questions_json():
    # Carregar ou criar o arquivo de questões
    if not os.path.exists(QUESTIONS_FILE):
        questions = extract_questions_from_pdf()
        with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        return questions
    
    # Ler o arquivo existente
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/questions", response_model=List[Question])
def get_questions():
    return load_questions()

@app.get("/api/questions/{question_id}", response_model=Question)
def get_question(question_id: int):
    questions = load_questions()
    for q in questions:
        if q["id"] == question_id:
            return q
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
    questionnaires = load_questionnaires()
    
    # Encontrar o questionário pelo ID
    questionnaire = None
    for q in questionnaires:
        if q["id"] == questionnaire_id:
            questionnaire = q
            break
    
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

@app.post("/api/questionnaires", response_model=Questionnaire)
def create_questionnaire(questionnaire: QuestionnaireCreate):
    questionnaires = load_questionnaires()
    
    # Gerar ID para o novo questionário
    new_id = 1
    if questionnaires:
        new_id = max(q["id"] for q in questionnaires) + 1
    
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
    
    questionnaires.append(new_questionnaire)
    save_questionnaires(questionnaires)
    
    # Expandir as questões para o retorno
    expanded_questions = [questions_dict[qid] for qid in valid_question_ids]
    
    return {
        "id": new_id,
        "title": questionnaire.title,
        "description": questionnaire.description,
        "questions": expanded_questions,
        "created_at": new_questionnaire["created_at"]
    }

@app.delete("/api/questionnaires/{questionnaire_id}", response_model=dict)
def delete_questionnaire(questionnaire_id: int):
    questionnaires = load_questionnaires()
    
    # Filtrar o questionário a ser removido
    updated_questionnaires = [q for q in questionnaires if q["id"] != questionnaire_id]
    
    if len(updated_questionnaires) == len(questionnaires):
        raise HTTPException(status_code=404, detail="Questionário não encontrado")
    
    save_questionnaires(updated_questionnaires)
    
    return {"message": "Questionário removido com sucesso"}

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
# RESPOSTAS DOS ALUNOS (BACKEND)
# ============================

RESPONSES_FILE = os.path.join(DATA_DIR, "responses.json")

def load_responses():
    if not os.path.exists(RESPONSES_FILE):
        return []
    with open(RESPONSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_response(new_response):
    responses = load_responses()
    responses.append(new_response)
    with open(RESPONSES_FILE, "w", encoding="utf-8") as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)

@app.get("/api/responses")
def get_all_responses():
    return load_responses()

@app.post("/api/responses")
async def receive_response(request: Request):
    try:
        data = await request.json()
        save_response(data)
        return {"message": "Resposta recebida com sucesso!"}
    except Exception as e:
        print("Erro ao salvar resposta:", e)
        raise HTTPException(status_code=400, detail="Erro ao processar os dados.")


# ============================
# ROTA SPA E INICIAL
# ============================

@app.get("/{path:path}")
async def serve_spa(path: str):
    file_path = os.path.join("static", path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join("static", "index.html"))

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
