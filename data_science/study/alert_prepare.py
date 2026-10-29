"""
Parte B, passo 1: rótulo de surto (canal endêmico) por série e mês.

- UF: todas as doenças × 27 UFs.
- Município: só séries com média >= MIN_MEAN_CASES_MUNICIPIO casos/mês
  até 2022 (as demais não têm casos para um canal estável).
Oropouche fica de fora (44 casos no período).

Grava OUTPUT_DIR/alert/labels_<nível>.parquet com series_id, casos,
limite do canal, surto (0/1; -1 sem 5 anos de histórico), população,
clima e covariáveis.
"""

import pandas as pd

from common import ALERT_DIR, MIN_MEAN_CASES_MUNICIPIO, endemic_channel, load_panel, series_keys

EXCLUDED = ["OROPOUCHE"]


def main() -> None:
    ALERT_DIR.mkdir(parents=True, exist_ok=True)

    for level in ("uf", "municipio"):
        panel = load_panel(level)
        panel = panel[~panel["disease"].isin(EXCLUDED)]
        panel["disease"] = panel["disease"].astype(str)
        keys = series_keys(level)

        if level == "municipio":
            mean_cases = panel[panel["ds"] < "2023-01-01"].groupby(keys)["y"].mean()
            eligible = mean_cases[mean_cases >= MIN_MEAN_CASES_MUNICIPIO].reset_index()[keys]
            panel = panel.merge(eligible, on=keys)

        labels = endemic_channel(panel, level)
        labels["series_id"] = labels[keys[0]] + "|" + labels[keys[1]].astype(str)
        labels.to_parquet(ALERT_DIR / f"labels_{level}.parquet", index=False)

        valid = labels[labels["outbreak"] >= 0]
        by_disease = valid.groupby("disease").agg(series=("series_id", "nunique"), surto_pct=("outbreak", "mean"))
        by_disease["surto_pct"] *= 100
        print(f"\n{level}: {labels['series_id'].nunique()} séries, {len(valid)} meses rotulados, "
              f"{valid['outbreak'].mean() * 100:.1f}% em surto")
        print(by_disease.round(1).to_string())


if __name__ == "__main__":
    main()
