"""
Junta as previsões de todos os modelos e calcula as métricas.

Grava em OUTPUT_DIR:
- metrics_overall.csv: por modelo (Brasil, as duas janelas juntas);
- metrics_by_disease.csv, metrics_by_state.csv, metrics_by_window.csv.

Todo modelo é avaliado nas mesmas linhas (série × mês das janelas de
teste); falta de previsão é erro, não linha ignorada.
"""

import pandas as pd

from common import OUTPUT_DIR, PREDICTIONS_DIR, load_dataset, metrics, windows


def targets() -> pd.DataFrame:
    df = load_dataset()
    return pd.concat(
        [target.assign(window=window) for window, _, target in windows(df)],
        ignore_index=True,
    )[["unique_id", "disease", "state", "ds", "window", "y"]]


def load_predictions(expected: pd.DataFrame) -> pd.DataFrame:
    frames = []

    for path in sorted(PREDICTIONS_DIR.glob("*.parquet")):
        predictions = pd.read_parquet(path)
        merged = expected.merge(predictions, on=["unique_id", "ds", "window"], how="left")
        missing = merged["y_hat"].isna().sum()
        if missing:
            raise ValueError(f"{path.stem}: {missing} linhas de teste sem previsão")
        frames.append(merged.assign(model=path.stem))

    return pd.concat(frames, ignore_index=True)


def table(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = [{**dict(zip(by, key if isinstance(key, tuple) else (key,))), **metrics(g["y"], g["y_hat"])}
            for key, g in df.groupby(by)]
    return pd.DataFrame(rows)


def state_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Soma município -> UF × doença × mês: o nível de um planejamento estadual."""

    return df.groupby(["model", "window", "state", "disease", "ds"], as_index=False)[["y", "y_hat"]].sum()


def main() -> None:
    expected = targets()
    df = load_predictions(expected)
    states = state_totals(df)

    overall = (
        table(df, ["model"])
        .merge(table(states, ["model"])[["model", "mae", "wape_pct"]], on="model", suffixes=("", "_uf"))
        .sort_values("wape_pct")
    )
    by_disease = table(df, ["disease", "model"]).merge(
        table(states, ["disease", "model"])[["disease", "model", "wape_pct"]], on=["disease", "model"], suffixes=("", "_uf")
    )
    by_state = table(df, ["state", "model"]).merge(
        table(states, ["state", "model"])[["state", "model", "wape_pct"]], on=["state", "model"], suffixes=("", "_uf")
    )
    by_window = table(df, ["window", "model"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    overall.to_csv(OUTPUT_DIR / "metrics_overall.csv", index=False)
    by_disease.to_csv(OUTPUT_DIR / "metrics_by_disease.csv", index=False)
    by_state.to_csv(OUTPUT_DIR / "metrics_by_state.csv", index=False)
    by_window.to_csv(OUTPUT_DIR / "metrics_by_window.csv", index=False)

    pd.set_option("display.width", 200)
    print(overall.round(3).to_string(index=False))
    print()
    print("WAPE por doença (município × mês):")
    print(by_disease.pivot(index="disease", columns="model", values="wape_pct").round(1).to_string())
    print()
    print("WAPE por doença (UF × mês):")
    print(by_disease.pivot(index="disease", columns="model", values="wape_pct_uf").round(1).to_string())


if __name__ == "__main__":
    main()
