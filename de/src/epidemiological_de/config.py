import os

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "affable-alpha-506516-r7")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "epidemiological_intelligence")
BIGQUERY_GOLD_TABLE = os.getenv("BIGQUERY_GOLD_TABLE", "epidemiology_climate_monthly")

GOLD_BIGQUERY_TABLE_ID = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_GOLD_TABLE}"

BUCKET = "epidemiological-intelligence"

# Raiz do bronze das fontes com ingestão automática (ingestion.py).
# Sobrescrevível por env para rodar localmente contra uma pasta
# (ex.: BRONZE_ROOT=file:///tmp/bronze) sem tocar no bucket.
BRONZE_ROOT = os.getenv("BRONZE_ROOT", f"gs://{BUCKET}/bronze")

# --- IBGE (dim_municipality) ---------------------------------------

IBGE_SOURCE = "ibge"

# Lista oficial de municípios (código de 7 dígitos, nome, UF, região).
IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

# Metadados da malha municipal: centróide (lat/lon) e área em km² por
# município, sem precisar baixar e processar os polígonos.
IBGE_MALHA_METADADOS_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR/metadados"
    "?intrarregiao=municipio"
)

# Polígonos dos municípios, para localizar em que município fica cada
# estação do INMET (inmet/stations.py). "intermediaria" (~12 MB): a
# "minima" erra estações perto da divisa.
IBGE_MALHA_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
    "?intrarregiao=municipio&formato=application/vnd.geo%2Bjson&qualidade=intermediaria"
)

DIM_MUNICIPALITY_SILVER_PATH = f"gs://{BUCKET}/silver/ibge/dim_municipality/"
DIM_MUNICIPALITY_TABLE = os.getenv("DIM_MUNICIPALITY_TABLE", "dim_municipality")
DIM_MUNICIPALITY_TABLE_ID = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{DIM_MUNICIPALITY_TABLE}"

INMET_BRONZE_PATH = f"gs://{BUCKET}/bronze/inmet/"
INMET_SILVER_PATH = f"gs://{BUCKET}/silver/inmet/"

# --- INMET (ingestão automática) -----------------------------------

INMET_SOURCE = "inmet"

# Um zip por ano com o CSV horário de todas as estações automáticas.
INMET_YEARLY_ZIP_URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"

# Primeiro ano da série de casos (SINAN/SIH); antes disso o clima não
# tem com o que cruzar.
INMET_FIRST_YEAR = int(os.getenv("INMET_FIRST_YEAR", "2015"))

# Estação -> município (inmet/stations.py) e agregado estação × mês;
# é o que o gold lê, em vez do silver horário.
INMET_STATIONS_SILVER_PATH = f"gs://{BUCKET}/silver/inmet_stations/"
INMET_STATION_MONTHLY_SILVER_PATH = f"gs://{BUCKET}/silver/inmet_station_monthly/"

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
