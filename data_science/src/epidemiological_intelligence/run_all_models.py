from epidemiological_intelligence.data.bigquery import (
    load_gold_from_bigquery,
)

from epidemiological_intelligence.modeling.configs import (
    MODEL_CONFIG,
)

from epidemiological_intelligence.pipeline.run_modeling import (
    run_disease_pipeline,
)


def run_all_models(df):

    results = {}

    for disease in MODEL_CONFIG:

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

    print("Carregando Gold do BigQuery...")

    df = load_gold_from_bigquery()

    print("Gold carregada.")
    print("Shape:", df.shape)

    print("\nExecutando modelos...")

    results = run_all_models(df)

    print("\nFinalizado.")
    print(
        f"Modelos concluídos: "
        f"{len(results)}/{len(MODEL_CONFIG)}"
    )


if __name__ == "__main__":
    main()