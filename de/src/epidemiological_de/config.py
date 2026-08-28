BUCKET = "epidemiological-intelligence"

INMET_BRONZE_PATH = f"gs://{BUCKET}/bronze/inmet/"
INMET_SILVER_PATH = f"gs://{BUCKET}/silver/inmet/"

SINAN_BRONZE_PATH = f"gs://{BUCKET}/bronze/sinan/"
SINAN_SILVER_PATH = f"gs://{BUCKET}/silver/sinan/"

GOLD_PATH = f"gs://{BUCKET}/gold/epidemiology_climate/"

SINAN_DISEASE_MAP = {
    "asma.csv": "ASMA",
    "bronquite_aguda.csv": "BRONQUITE AGUDA",
    "bronquite_cronica.csv": "BRONQUITE CRÔNICA",
    "infarto.csv": "INFARTO AGUDO DO MIOCÁRDIO",
    "insuficiencia_cardiaca.csv": "INSUFICIÊNCIA CARDÍACA",
    "lesptospirose.csv": "LEPTOSPIROSE",
}
