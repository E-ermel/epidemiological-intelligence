import pandas as pd

from epidemiological_intelligence.modeling.configs import (
    MODEL_CONFIG,
)

from epidemiological_intelligence.pipeline.run_modeling import (
    run_disease_pipeline,
)


def run_all_models(
    df: pd.DataFrame,
):

    results = {}

    for disease in MODEL_CONFIG:

        print(
            f"\n{'=' * 60}"
        )

        print(
            f"Treinando: {disease}"
        )

        print(
            f"{'=' * 60}"
        )

        try:

            result = run_disease_pipeline(
                df=df,
                disease=disease,
            )

            results[disease] = result

            metrics = result[
                "comparison"
            ]

            print(
                "MAE:",
                round(
                    metrics[
                        "final"
                    ]["mae"],
                    4,
                )
            )

            print(
                "RMSE:",
                round(
                    metrics[
                        "final"
                    ]["rmse"],
                    4,
                )
            )

            print(
                "R²:",
                round(
                    metrics[
                        "final"
                    ]["r2"],
                    4,
                )
            )

            print(
                "Melhora RMSE:",
                round(
                    metrics[
                        "rmse_improvement_pct"
                    ],
                    2,
                ),
                "%",
            )

        except Exception as error:

            print(
                f"Erro em {disease}:"
            )

            print(error)

    return results