import json
from pathlib import Path

import pandas as pd


def save_metrics(
    disease: str,
    metrics: dict,
    output_dir: str = "artifacts/modeling",
):
    output_path = Path(output_dir) / disease.lower().replace(" ", "_")

    output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = output_path / "metrics.json"

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            metrics,
            file,
            indent=4,
            ensure_ascii=False
        )

    return file_path

def save_predictions(
    disease: str,
    predictions: pd.DataFrame,
    output_dir: str = "artifacts/modeling",
):
    output_path = Path(output_dir) / disease.lower().replace(" ", "_")

    output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = output_path / "predictions.parquet"

    predictions.to_parquet(
        file_path,
        index=False
    )

    return file_path

def save_municipality_metrics(
    disease: str,
    municipality_metrics: pd.DataFrame,
    output_dir: str = "artifacts/modeling",
):
    output_path = Path(output_dir) / disease.lower().replace(" ", "_")

    output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = output_path / "municipality_metrics.parquet"

    municipality_metrics.to_parquet(
        file_path,
        index=False
    )

    return file_path