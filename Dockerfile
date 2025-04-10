FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Criar diretórios necessários
RUN mkdir -p data static

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application directly (não usando o __main__)
CMD python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
