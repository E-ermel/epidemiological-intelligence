TRAIN_END = "2023-12-01"
TEST_START = "2024-01-01"

MODEL_CONFIG = {
    "ASMA": {
        "features": [
            "relative_humidity_avg_pct",
            "dew_point_avg_c_lag1",
        ],
    },

    "BRONQUITE AGUDA": {
        "features": [
            "relative_humidity_avg_pct",
            "precipitation_avg_observation_mm_lag3",
        ],
    },

    "BRONQUITE CRÔNICA": {
        "features": [
            "wind_gust_max_ms",
        ],
    },

    "INFARTO AGUDO DO MIOCÁRDIO": {
        "features": [
            "wind_speed_avg_ms_lag1",
        ],
    },

    "INSUFICIÊNCIA CARDÍACA": {
        "features": [
            "atmospheric_pressure_avg_mb",
            "dew_point_avg_c",
        ],
    },

    "LEPTOSPIROSE": {
        "features": [
            "precipitation_sum_mm_lag1",
            "relative_humidity_avg_pct_lag1",
        ],
    },
}