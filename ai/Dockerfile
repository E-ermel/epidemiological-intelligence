FROM python:3.12-slim

WORKDIR /app


# Instala dependências primeiro
COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    -r requirements.txt


# Copia o código da aplicação
COPY src ./src


# Copia o índice vetorial pronto
COPY chroma_db ./chroma_db


# Caso o runtime ou scripts precisem consultar
# a documentação original
COPY knowledge ./knowledge


# Faz Python localizar nosso pacote em /app/src
ENV PYTHONPATH=/app/src


# Cloud Run utiliza 8080 por padrão
EXPOSE 8080


CMD ["sh", "-c", "uvicorn epidemiological_agent.api.app:app --host 0.0.0.0 --port ${PORT:-8080}"]