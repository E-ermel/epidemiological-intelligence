"""
Job mensal do alerta de surtos.

    python -m epidemiological_intelligence.alert.run [--origin AAAA-MM] [--levels uf municipio]

Lê o gold (BigQuery; ou GOLD_PARQUET_DIR localmente), monta os painéis,
prevê a partir das duas origens de cada doença (mês fechado e mês
provisório) e publica (BigQuery + GCS; ou ALERT_OUTPUT_DIR localmente).
`--origin` força a mesma origem para tudo (validação contra o estudo).
"""

import argparse
import os
import time

import pandas as pd

from epidemiological_intelligence.alert import config, data, forecast, prepare, publish


def run(
    cases: pd.DataFrame,
    context: pd.DataFrame,
    forecaster: forecast.Forecaster,
    levels: list[str],
    origin: pd.Timestamp | None = None,
) -> pd.DataFrame:
    origins = prepare.disease_origins(cases, override=origin)
    eligible = prepare.eligible_municipal_series(cases, origins)
    last_month = origins["origin"].max() + pd.DateOffset(months=max(config.HORIZONS))
    print(origins.drop_duplicates(["source", "origin_type"]).to_string(index=False), flush=True)

    frames = []
    for level in levels:
        start = time.time()
        panel = prepare.build_panel(level, cases, context, eligible, last_month)
        print(f"{level}: {panel['series_id'].nunique()} séries", flush=True)
        for (origin_type, when), group in origins.groupby(["origin_type", "origin"]):
            frames.append(
                forecast.forecast_origin(panel, level, group["disease"].tolist(), when, origin_type, forecaster)
            )
        print(f"{level}: {time.time() - start:.0f}s", flush=True)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", type=pd.Timestamp, default=None)
    parser.add_argument("--levels", nargs="+", default=config.LEVELS, choices=config.LEVELS)
    args = parser.parse_args()

    gold_dir = os.getenv("GOLD_PARQUET_DIR")
    cases, context = data.load_from_parquet(gold_dir) if gold_dir else data.load_from_bigquery()
    print(f"gold: {len(cases)} linhas de casos, {len(context)} município-meses", flush=True)

    run_id = pd.Timestamp.now(tz="UTC").floor("s")
    alerts = run(cases, context, forecast.chronos_forecaster(), args.levels, args.origin)
    alerts["run_id"] = run_id
    alerts["model_version"] = config.MODEL_VERSION
    meta = publish.summary(alerts, run_id)

    output_dir = os.getenv("ALERT_OUTPUT_DIR")
    if output_dir:
        publish.to_local(alerts, meta, output_dir)
    else:
        publish.to_cloud(alerts, meta)
    print(f"{len(alerts)} linhas, {int(alerts['alert'].sum())} alertas", flush=True)


if __name__ == "__main__":
    main()
