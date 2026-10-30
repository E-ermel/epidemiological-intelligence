"""
Configuração do alerta de surtos (Chronos-2 + clima passado +
cross-learning), escolhido no estudo em data_science/study/.

Os cortes e as métricas vêm do teste 2024-2025 (corte escolhido em 2023
pelo maior F1); mudar o modelo exige refazer o estudo e trocar
MODEL_VERSION.
"""

import os

MODEL_VERSION = "chronos2-clima-cross-v1"
CHRONOS_MODEL = os.getenv("CHRONOS_MODEL", "amazon/chronos-2")
CHRONOS_DEVICE = os.getenv("CHRONOS_DEVICE", "cpu")
# Cross-learning: lotes de ~100 séries em ordem de id ("DOENÇA|UF",
# "DOENÇA|município") reúnem a mesma doença em lugares vizinhos.
CROSS_LEARNING_BATCH = 100
QUANTILE_LEVELS = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]

LEVELS = ["uf", "municipio"]
HORIZONS = [1, 2, 3]

# Clima do mês usado como covariável passada.
CLIMATE = [
    "precipitation_sum_mm",
    "precipitation_max_observation_mm",
    "temperature_avg_c",
    "relative_humidity_avg_pct",
]

# Oropouche: poucos casos para um canal endêmico estável.
EXCLUDED_DISEASES = ["OROPOUCHE"]

# --- Surto (canal endêmico) -----------------------------------------
CHANNEL_YEARS = 5
CHANNEL_Z = 1.96
MIN_CASES = {"uf": 5, "municipio": 3}
# Anos fora do canal, por fonte: a queda de internações na pandemia
# inflava o desvio do canal do SIH e escondia surtos (estudo: F1 da UF
# 0,538 -> 0,555). O canal pega os 5 anos anteriores mais recentes fora
# da lista. O SINAN não teve a queda e fica com o canal normal.
CHANNEL_EXCLUDED_YEARS = {"SIH": [2020, 2021]}

# Série municipal entra no alerta com média >= 1 caso/mês nos 60 meses
# até a origem fechada; as demais ficam só no alerta da UF.
MIN_MEAN_CASES_MUNICIPIO = 1.0
ELIGIBILITY_MONTHS = 60

# --- Origens ---------------------------------------------------------
# provisório: último mês com dados; um mês com menos de
# PARTIAL_MONTH_SHARE dos casos do mês anterior está em andamento e sai.
# fechado: SIH = último mês sem is_provisional (a marca é por mês);
# SINAN = SINAN_CLOSED_LAG_MONTHS antes do último mês com dados (a marca
# do SINAN cobre o ano preliminar inteiro, que já vem quase completo).
PARTIAL_MONTH_SHARE = 0.5
SINAN_CLOSED_LAG_MONTHS = 2
# Fontes com um arquivo por agravo, cada um com sua data de atualização:
# a origem é calculada por doença, não pela fonte inteira.
ORIGIN_BY_DISEASE_SOURCES = ["SINAN"]
ORIGIN_TYPES = ["fechado", "provisorio"]

# --- Corte e métricas do teste (estudo, 2024-2025) ------------------
# Canal misto (SIH sem 2020-2021), study/alert_mix.py.
CUTOFFS = {"uf": 0.2995, "municipio": 0.1990}
TEST_METRICS = {
    "uf": {"precision": 0.561, "recall": 0.549, "f1": 0.555, "auc_pr": 0.589, "auc_roc": 0.834,
           "brier": 0.122, "test_predictions": 23328, "outbreak_pct": 20.7},
    "municipio": {"precision": 0.334, "recall": 0.539, "f1": 0.412, "auc_pr": 0.379, "auc_roc": 0.808,
                  "brier": 0.085, "test_predictions": 827208, "outbreak_pct": 11.3},
}

# --- Destino ---------------------------------------------------------
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "epidemiological_intelligence")
BIGQUERY_GOLD_TABLE = os.getenv("BIGQUERY_GOLD_TABLE", "epidemiology_climate_monthly_br")
BIGQUERY_ALERT_TABLE = os.getenv("BIGQUERY_ALERT_TABLE", "outbreak_alerts")
ARTIFACT_BUCKET = os.getenv("ARTIFACT_BUCKET", "epidemiological-intelligence")
ALERT_ARTIFACT_PREFIX = os.getenv("ALERT_ARTIFACT_PREFIX", "alert")
