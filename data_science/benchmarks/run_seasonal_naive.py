"""Referência: cada mês previsto = o mesmo mês do ano anterior à origem."""

import pandas as pd

from common import HORIZON, load_dataset, save_predictions, windows


def main() -> None:
    df = load_dataset()
    predictions = []

    for window, history, target in windows(df):
        last_year = history[history["ds"] > history["ds"].max() - pd.DateOffset(months=HORIZON)]
        last_year = last_year.assign(ds=last_year["ds"] + pd.DateOffset(months=HORIZON))

        predicted = target[["unique_id", "ds"]].merge(
            last_year[["unique_id", "ds", "y"]].rename(columns={"y": "y_hat"}),
            on=["unique_id", "ds"],
            how="left",
        )
        predictions.append(predicted.assign(window=window, y_hat=predicted["y_hat"].fillna(0)))

    save_predictions(pd.concat(predictions, ignore_index=True), "seasonal_naive")


if __name__ == "__main__":
    main()
