import os

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "affable-alpha-506516-r7")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "epidemiological_intelligence")

# Gold nacional. A tabela anterior (epidemiology_climate_monthly, 27
# municípios do RS) não é mais escrita e fica no dataset para rollback.
BIGQUERY_GOLD_TABLE = os.getenv("BIGQUERY_GOLD_TABLE", "epidemiology_climate_monthly_br")

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

# Resultado de cada ano processado (estação × mês, metadados das
# estações e o sha256 do zip de origem): um ano só é reprocessado
# quando o zip dele mudou no bronze.
INMET_YEARS_SILVER_PATH = f"gs://{BUCKET}/silver/inmet_years/"
INMET_STATION_MONTHLY_SILVER_PATH = f"gs://{BUCKET}/silver/inmet_station_monthly/"

# --- DATASUS (FTP) -------------------------------------------------

DATASUS_FTP_HOST = "ftp.datasus.gov.br"

# As 27 UFs, na ordem em que os jobs por UF dividem o trabalho entre
# as tasks do Cloud Run (ver sih/ingest.py).
UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

# --- SIH/SUS (internações) -----------------------------------------

SIH_SOURCE = "sih"

# AIH reduzida (RD{UF}{AA}{MM}.dbc), um arquivo por UF e competência de
# processamento, desde 2008.
SIH_FTP_DIR = "/dissemin/publicos/SIHSUS/200801_/Dados"

# Primeira competência baixada. Internações de um mês aparecem em
# competências posteriores, nunca anteriores, então começar no mesmo
# ano da série de casos não perde nada.
SIH_FIRST_YEAR = int(os.getenv("SIH_FIRST_YEAR", "2015"))

# AIHs atrasadas: em internações do RS em 2023, só 0,13% chegaram mais
# de 4 meses depois do mês da internação. Os meses mais recentes que
# isso (em relação à última competência da UF) saem marcados como
# provisórios.
SIH_PROVISIONAL_MONTHS = 4

# Internações por doença × residência × internação × mês, partição por UF.
SIH_SILVER_PATH = f"gs://{BUCKET}/silver/sih_hospitalizations/"

# --- SINAN (notificações) ------------------------------------------

SINAN_SOURCE = "sinan"

# Um arquivo nacional por agravo e ano ({AGRAVO}BR{AA}.dbc). Anos com
# base fechada ficam em FINAIS; os recentes em PRELIM, até fecharem.
SINAN_FTP_DIRS = {
    "FINAIS": "/dissemin/publicos/SINAN/DADOS/FINAIS",
    "PRELIM": "/dissemin/publicos/SINAN/DADOS/PRELIM",
}

# LEPT: leptospirose; ANIM: acidentes por animais peçonhentos.
SINAN_AGRAVOS = ["LEPT", "ANIM"]

SINAN_FIRST_YEAR = int(os.getenv("SINAN_FIRST_YEAR", "2015"))

# Casos por doença × residência × local do evento × mês.
SINAN_SILVER_PATH = f"gs://{BUCKET}/silver/sinan_cases/"

# --- SIDRA/IBGE (população) ----------------------------------------

SIDRA_SOURCE = "sidra"

SIDRA_API = "https://apisidra.ibge.gov.br/values"

# Estimativas anuais de população por município (tabela 6579, variável
# 9324). A API limita 50 mil valores por consulta: um ano por vez.
SIDRA_ESTIMATES_URL = f"{SIDRA_API}/t/6579/n6/all/v/9324/p/{{year}}"
# Mesma tabela no nível Brasil: só para descobrir quais anos existem.
SIDRA_ESTIMATE_YEARS_URL = f"{SIDRA_API}/t/6579/n1/all/v/9324/p/all"

# População residente do Censo 2022 (tabela 4709, variável 93): não há
# estimativa para 2022, e o censo é a contagem de referência.
SIDRA_CENSUS_2022_URL = f"{SIDRA_API}/t/4709/n6/all/v/93/p/2022"

SIDRA_FIRST_YEAR = 2015

# População e densidade por município × ano.
POPULATION_SILVER_PATH = f"gs://{BUCKET}/silver/sidra_population/"

# --- Atlas Brasil (IDHM), via Base dos Dados -----------------------

ATLAS_SOURCE = "atlas"

# Cópia pública do Atlas do Desenvolvimento Humano (PNUD/IPEA/FJP) no
# BigQuery da Base dos Dados (🔵 espelho): o site do Atlas não oferece
# download automatizável. Censos de 1991, 2000 e 2010.
ATLAS_BIGQUERY_TABLE = "basedosdados.mundo_onu_adh.municipio"

ATLAS_SILVER_PATH = f"gs://{BUCKET}/silver/atlas_idhm/"

# --- MapBiomas (uso e cobertura da terra), via Base dos Dados ------

MAPBIOMAS_SOURCE = "mapbiomas"

# 🟠 rede MapBiomas (não oficial), pela cópia da Base dos Dados (🔵): o
# site troca a URL da planilha a cada coleção.
MAPBIOMAS_BIGQUERY_TABLE = "basedosdados.br_mapbiomas_estatisticas.cobertura_municipio_classe"

MAPBIOMAS_FIRST_YEAR = 2015

LAND_COVER_SILVER_PATH = f"gs://{BUCKET}/silver/mapbiomas_land_cover/"

# --- Gold ----------------------------------------------------------

# Um parquet por doença (part-NN.parquet); o BigQuery carrega a pasta.
GOLD_PATH = f"gs://{BUCKET}/gold/epidemiology_climate_br/"

# Município sem estação do INMET (ou sem dado dela no mês) usa a
# estação mais próxima com dado, até esta distância do centróide.
CLIMATE_MAX_DISTANCE_KM = float(os.getenv("CLIMATE_MAX_DISTANCE_KM", "100"))

# Primeiro mês do gold: o mesmo das séries de casos.
GOLD_FIRST_YEAR = 2015
