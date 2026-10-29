"""
Parte B, ensemble: média das probabilidades de surto de vários modelos,
nas linhas que todos preveem. Grava como um modelo a mais
(OUTPUT_DIR/alert/<ensemble>_<nível>.parquet) para alert_evaluate.py.

- ensemble_fundacao: Chronos-2, Chronos-2 + clima, TimesFM, Moirai 2 e
  PatchTST (os que lideram na UF);
- ensemble_todos: os anteriores + GLM, LightGBM classificador e TFT;
- ensemble_todos_cross: ensemble_todos + Chronos-2 com cross-learning.

Uso: python alert_ensemble.py
"""

import pandas as pd

from common import ALERT_DIR, save_alert

ENSEMBLES = {
    "ensemble_fundacao": ["chronos2", "chronos2_clima", "timesfm", "moirai2", "patchtst"],
    "ensemble_todos": ["chronos2", "chronos2_clima", "timesfm", "moirai2", "patchtst", "glm_nb",
                       "lgbm_classificador", "tft"],
    "ensemble_todos_cross": ["chronos2", "chronos2_clima", "chronos2_clima_cross", "timesfm", "moirai2", "patchtst",
                             "glm_nb", "lgbm_classificador", "tft"],
}
KEY = ["level", "series_id", "disease", "state", "ds", "horizon"]


def main() -> None:
    for level in ("uf", "municipio"):
        for name, members in ENSEMBLES.items():
            frames = [
                pd.read_parquet(ALERT_DIR / f"{m}_{level}.parquet")
                .astype({"ds": "datetime64[ns]", "horizon": "int64", "disease": str, "state": str})
                .dropna(subset=["probability"])
                for m in members
            ]
            df = pd.concat(frames, ignore_index=True)
            mean = df.groupby(KEY, observed=True)["probability"].agg(["mean", "count"]).reset_index()
            mean = mean[mean["count"] == len(members)].rename(columns={"mean": "probability"})
            save_alert(mean[KEY + ["probability"]], f"{name}_{level}")


if __name__ == "__main__":
    main()
