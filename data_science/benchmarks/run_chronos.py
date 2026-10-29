"""
Chronos-2 (Amazon), zero-shot. Duas variantes:

- chronos2: só o histórico de casos;
- chronos2_clima: + clima observado como covariável, inclusive nos 12
  meses previstos (cenário "clima conhecido", como no modelo atual).
"""

import pandas as pd
import torch
from chronos import BaseChronosPipeline

from common import CLIMATE_COLUMNS, HORIZON, load_dataset, save_predictions, windows

CHECKPOINT = "amazon/chronos-2"


def _rename(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"unique_id": "item_id", "ds": "timestamp", "y": "target"})


def forecast(pipeline, history: pd.DataFrame, target: pd.DataFrame, with_climate: bool) -> pd.DataFrame:
    covariates = CLIMATE_COLUMNS if with_climate else []

    predicted = pipeline.predict_df(
        _rename(history[["unique_id", "ds", "y", *covariates]]),
        future_df=_rename(target[["unique_id", "ds", *covariates]]) if with_climate else None,
        prediction_length=HORIZON,
        quantile_levels=[0.5],
        batch_size=512,
        freq="MS",
    )

    # Mediana: minimiza o erro absoluto (MAE/WAPE).
    return predicted.rename(columns={"item_id": "unique_id", "timestamp": "ds", "0.5": "y_hat"})[
        ["unique_id", "ds", "y_hat"]
    ]


def main() -> None:
    pipeline = BaseChronosPipeline.from_pretrained(CHECKPOINT, device_map="cuda", torch_dtype=torch.bfloat16)
    df = load_dataset()

    for name, with_climate in (("chronos2", False), ("chronos2_clima", True)):
        predictions = []
        for window, history, target in windows(df):
            predictions.append(forecast(pipeline, history, target, with_climate).assign(window=window))
            print(f"{name} janela {window}: ok")
        save_predictions(pd.concat(predictions, ignore_index=True), name)


if __name__ == "__main__":
    main()
