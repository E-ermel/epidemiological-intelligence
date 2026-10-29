FROM python:3.12-slim

WORKDIR /app

# torch só de CPU (o job do alerta roda sem GPU) e o Chronos-2 ficam
# fora do requirements.txt para os testes do CI não baixarem o torch.
# Versões validadas no estudo (data_science/study); transformers sem
# pino puxa a 5.x, que exige torch >= 2.6 e quebra o chronos 2.3.2.
RUN pip install --no-cache-dir torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir chronos-forecasting==2.3.2 transformers==4.49.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pesos do Chronos-2 dentro da imagem: o job não depende do Hugging Face.
ENV CHRONOS_MODEL=/models/chronos-2
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('amazon/chronos-2', local_dir='/models/chronos-2')"
ENV HF_HUB_OFFLINE=1

COPY src ./src

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "epidemiological_intelligence.alert.run"]
