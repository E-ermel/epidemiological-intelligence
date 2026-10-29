"""
TimesFM 2.5 (Google), zero-shot, só com o histórico de casos. A
regressão em covariáveis do TimesFM (xreg) depende de JAX com CUDA,
que não roda no Windows; por isso não há variante com clima.
"""

import numpy as np
import pandas as pd
import timesfm

from common import HORIZON, load_dataset, save_predictions, windows

CHECKPOINT = "google/timesfm-2.5-200m-pytorch"
BATCH = 1024


def main() -> None:
    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(CHECKPOINT)
    model.compile(
        timesfm.ForecastConfig(
            max_context=128,
            max_horizon=128,
            normalize_inputs=True,
            use_continuous_quantile_head=True,
            infer_is_positive=True,
            fix_quantile_crossing=True,
            per_core_batch_size=BATCH,
        )
    )

    df = load_dataset()
    predictions = []

    for window, history, target in windows(df):
        series = history.groupby("unique_id", sort=True)["y"].apply(lambda s: s.to_numpy(dtype=np.float32))
        ids = series.index.to_list()

        point, quantiles = model.forecast(horizon=HORIZON, inputs=series.to_list())
        # quantiles[..., 5] é a mediana (índice 0 = média, 1..9 = q10..q90).
        median = np.asarray(quantiles)[:, :HORIZON, 5]

        future = pd.date_range(history["ds"].max() + pd.DateOffset(months=1), periods=HORIZON, freq="MS")
        predictions.append(
            pd.DataFrame(
                {
                    "unique_id": np.repeat(ids, HORIZON),
                    "ds": np.tile(future, len(ids)),
                    "y_hat": median.reshape(-1),
                    "window": window,
                }
            )
        )
        print(f"timesfm janela {window}: {len(ids)} séries")

    save_predictions(pd.concat(predictions, ignore_index=True), "timesfm")


if __name__ == "__main__":
    main()
