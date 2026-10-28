"""
Moirai 2.0 (Salesforce), zero-shot. Duas variantes:

- moirai2: só o histórico de casos;
- moirai2_clima: + clima como covariável conhecida no futuro
  (feat_dynamic_real cobre o histórico e os 12 meses previstos).
"""

import sys

import numpy as np
import pandas as pd
from uni2ts.model.moirai2 import Moirai2Forecast, Moirai2Module

from common import CLIMATE_COLUMNS, HORIZON, load_dataset, save_predictions, windows

CHECKPOINT = "Salesforce/moirai-2.0-R-small"
BATCH = 512
CONTEXT = 120


def _model(module, covariates: int) -> Moirai2Forecast:
    return Moirai2Forecast(
        module=module,
        prediction_length=HORIZON,
        context_length=CONTEXT,
        target_dim=1,
        feat_dynamic_real_dim=covariates,
        past_feat_dynamic_real_dim=0,
    ).to("cuda")


def forecast(model, history: pd.DataFrame) -> pd.DataFrame:
    """Só histórico: Moirai2Forecast.predict direto, em lotes."""

    history = history.sort_values(["unique_id", "ds"])
    ids = history["unique_id"].unique()
    past = [g.to_numpy(dtype=np.float32)[:, None] for _, g in history.groupby("unique_id", sort=True)["y"]]

    medians = []
    for start in range(0, len(past), BATCH):
        # [lote, quantis (0.1..0.9), tempo]: o do meio é a mediana.
        quantiles = np.asarray(model.predict(past[start:start + BATCH]))
        medians.append(quantiles[:, quantiles.shape[1] // 2, :HORIZON].reshape(len(quantiles), HORIZON))

    future = pd.date_range(history["ds"].max() + pd.DateOffset(months=1), periods=HORIZON, freq="MS")
    return pd.DataFrame(
        {
            "unique_id": np.repeat(ids, HORIZON),
            "ds": np.tile(future, len(ids)),
            "y_hat": np.concatenate(medians).reshape(-1),
        }
    )


def forecast_with_climate(model, history: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    """
    Com clima: pelo preditor do GluonTS. O predict() direto corta as
    covariáveis no tamanho do contexto, então não serve quando elas se
    estendem pelos meses previstos.
    """

    from gluonts.dataset.pandas import PandasDataset

    full = pd.concat([history, target]).sort_values(["unique_id", "ds"])
    dataset = PandasDataset.from_long_dataframe(
        full[["unique_id", "ds", "y", *CLIMATE_COLUMNS]],
        item_id="unique_id",
        timestamp="ds",
        target="y",
        feat_dynamic_real=CLIMATE_COLUMNS,
        future_length=HORIZON,
        freq="M",  # o GluonTS converte para período; "MS" não é frequência de período
    )

    rows = []
    for item in model.create_predictor(batch_size=BATCH).predict(dataset):
        future = item.index.to_timestamp()
        rows.append(pd.DataFrame({"unique_id": item.item_id, "ds": future, "y_hat": item.quantile(0.5)}))

    return pd.concat(rows, ignore_index=True)


def main() -> None:
    module = Moirai2Module.from_pretrained(CHECKPOINT)
    df = load_dataset()

    variants = sys.argv[1:] or ["moirai2", "moirai2_clima"]

    for name in variants:
        with_climate = name.endswith("_clima")
        model = _model(module, len(CLIMATE_COLUMNS) if with_climate else 0)
        predictions = []
        for window, history, target in windows(df):
            predicted = forecast_with_climate(model, history, target) if with_climate else forecast(model, history)
            predictions.append(predicted.assign(window=window))
            print(f"{name} janela {window}: ok")
        save_predictions(pd.concat(predictions, ignore_index=True), name)


if __name__ == "__main__":
    main()
