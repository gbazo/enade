from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

# Inicializa a aplicação FastAPI
app = FastAPI(title="Sistema de Questionários ENADE")

# Configuração CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rota principal
@app.get("/")
async def read_root():
    return {"message": "Sistema de Questionários ENADE API está funcionando!"}

# Rota de teste
@app.get("/api/test")
async def test_api():
    return {"status": "success", "port": os.environ.get("PORT", "8000")}
