import os
import shutil
import json
import subprocess
import sys

def check_dependencies():
    """Verifica se as dependências necessárias estão instaladas."""
    try:
        import fastapi
        import uvicorn
        import pydantic
        print("✅ Dependências já instaladas.")
        return True
    except ImportError:
        print("⚠️ Algumas dependências estão faltando.")
        return False

def install_dependencies():
    """Instala as dependências necessárias."""
    print("📦 Instalando dependências...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "pydantic"])
    print("✅ Dependências instaladas com sucesso.")

def setup_directories():
    """Configura os diretórios necessários para o aplicativo."""
    # Criar diretório de dados
    if not os.path.exists("data"):
        os.makedirs("data")
        print("✅ Diretório 'data' criado.")
    
    # Criar diretório static para arquivos frontend
    if not os.path.exists("static"):
        os.makedirs("static")
        print("✅ Diretório 'static' criado.")
    
    # Criar diretório de logs
    if not os.path.exists("logs"):
        os.makedirs("logs")
        print("✅ Diretório 'logs' criado.")

def setup_frontend_files():
    """Cria ou copia os arquivos do frontend para o diretório static."""
    # Verificar se os arquivos HTML, CSS e JS existem na pasta static
    html_path = os.path.join("static", "index.html")
    css_path = os.path.join("static", "styles.css")
    js_path = os.path.join("static", "script.js")
    
    # Se não existirem, criar arquivos modelo
    if not os.path.exists(html_path):
        if os.path.exists("index.html"):
            shutil.copy("index.html", html_path)
            print("✅ Arquivo index.html copiado para a pasta static.")
        else:
            print("❌ Arquivo index.html não encontrado. Por favor, crie-o manualmente.")
    
    if not os.path.exists(css_path):
        if os.path.exists("styles.css"):
            shutil.copy("styles.css", css_path)
            print("✅ Arquivo styles.css copiado para a pasta static.")
        else:
            print("❌ Arquivo styles.css não encontrado. Por favor, crie-o manualmente.")
    
    if not os.path.exists(js_path):
        if os.path.exists("script.js"):
            shutil.copy("script.js", js_path)
            print("✅ Arquivo script.js copiado para a pasta static.")
        else:
            print("❌ Arquivo script.js não encontrado. Por favor, crie-o manualmente.")

def create_sample_questions():
    """Cria um arquivo de questões de exemplo caso não exista."""
    questions_path = os.path.join("data", "questions.json")
    
    if not os.path.exists(questions_path):
        # Questões de exemplo
        questions = []
        
        with open(questions_path, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        
        print("✅ Arquivo de questões de exemplo criado.")
    else:
        print("✅ Arquivo de questões já existe.")

def create_empty_questionnaires():
    """Cria um arquivo de questionários vazio se não existir."""
    questionnaires_path = os.path.join("data", "questionnaires.json")
    
    if not os.path.exists(questionnaires_path):
        with open(questionnaires_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        
        print("✅ Arquivo de questionários vazio criado.")
    else:
        print("✅ Arquivo de questionários já existe.")

def check_main_file():
    """Verifica se o arquivo main.py existe."""
    if not os.path.exists("main.py"):
        print("⚠️ Arquivo main.py não encontrado. Por favor, crie-o manualmente.")
        return False
    return True

def start_server():
    """Inicia o servidor FastAPI."""
    if not check_main_file():
        return
    
    try:
        import uvicorn
        print("🚀 Iniciando servidor...")
        print("📊 Acesse o sistema em: http://localhost:8000")
        os.system("uvicorn main:app --reload")
    except Exception as e:
        print(f"⚠️ Erro ao iniciar o servidor: {e}")

def main():
    """Função principal para configurar e iniciar o sistema."""
    print("=" * 50)
    print("🔧 Configurando o Sistema de Questionários ENADE (Versão Refatorada)")
    print("=" * 50)
    
    # Verificar e instalar dependências
    if not check_dependencies():
        install_dependencies()
    
    # Configurar diretórios
    setup_directories()
    
    # Configurar arquivos frontend
    setup_frontend_files()
    
    # Criar arquivos de dados de exemplo
    create_sample_questions()
    create_empty_questionnaires()
    
    # Iniciar o servidor
    start_server()

if __name__ == "__main__":
    main()