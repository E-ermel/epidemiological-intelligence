import os

from epidemiological_intelligence.data.bigquery import (
    load_gold_from_bigquery,
)

from epidemiological_intelligence.modeling.configs import (
    MODEL_CONFIG,
)

from epidemiological_intelligence.pipeline.run_modeling import (
    run_disease_pipeline,
)


def run_all_models(df, diseases=None):

    diseases = list(diseases) if diseases is not None else list(MODEL_CONFIG)

    results = {}

    for disease in diseases:

        print("\n" + "=" * 60)
        print(f"Treinando: {disease}")
        print("=" * 60)

        try:
            result = run_disease_pipeline(
                df=df,
                disease=disease,
            )

            results[disease] = result

            metrics = result["comparison"]

            print("MAE:", metrics["final"]["mae"])
            print("RMSE:", metrics["final"]["rmse"])
            print("R²:", metrics["final"]["r2"])
            print("WAPE:", metrics["final"]["wape_pct"])
            print(
                "Melhora RMSE:",
                metrics["rmse_improvement_pct"],
            )

        except Exception as error:
            print(
                f"Erro em {disease}: "
                f"{type(error).__name__}: {error}"
            )

    return results


def main():

    # Cloud Run Job execution override -- lets the retrain trigger in
    # ai/ (see api/retrain_job.py) ask for a single disease instead of
    # the full run. Unset (the scheduled/Airflow-driven run) trains
    # every disease in MODEL_CONFIG, same as before.
    disease_filter = os.environ.get("DISEASE_FILTER")

    if disease_filter and disease_filter not in MODEL_CONFIG:
        raise ValueError(
            f"DISEASE_FILTER={disease_filter!r} is not a known disease. "
            f"Expected one of: {sorted(MODEL_CONFIG)}"
        )

    diseases = [disease_filter] if disease_filter else list(MODEL_CONFIG)

    print("Carregando Gold do BigQuery...")

    df = load_gold_from_bigquery()

    print("Gold carregada.")
    print("Shape:", df.shape)

    print("\nExecutando modelos...")

    results = run_all_models(df, diseases=diseases)

    print("\nFinalizado.")
    print(
        f"Modelos concluídos: "
        f"{len(results)}/{len(diseases)}"
    )


if __name__ == "__main__":
    main()