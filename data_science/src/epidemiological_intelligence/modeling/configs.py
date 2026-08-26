# src/epidemiological_intelligence/modeling/config.py

TRAIN_END = "2023-12-01"
TEST_START = "2024-01-01"

TARGET = "cases"

ID_COLUMNS = [
    "municipality",
    "reference_date",
    "disease",
]

BASE_FEATURES = [
    "municipality",
    "month",
]

MODEL_CONFIG = {
    "ASMA": {
        "model": "negative_binomial",
        "features": [],
    },

    "BRONQUITE AGUDA": {
        "model": "negative_binomial",
        "features": [],
    },

    "BRONQUITE CRÔNICA": {
        "model": "negative_binomial",
        "features": [],
    },

    "INFARTO AGUDO DO MIOCÁRDIO": {
        "model": "negative_binomial",
        "features": [],
    },

    "INSUFICIÊNCIA CARDÍACA": {
        "model": "negative_binomial",
        "features": [],
    },

    "LEPTOSPIROSE": {
        "model": "negative_binomial",
        "features": [
        ],
    },
}