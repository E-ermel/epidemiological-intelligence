import pandas as pd

from epidemiological_intelligence.data.preparation import (
    prepare_model_data,
)

from epidemiological_intelligence.features.lags import (
    create_climate_lags,
)

from epidemiological_intelligence.modeling.configs import (
    MODEL_CONFIG,
    TEST_START,
)

from epidemiological_intelligence.modeling.train import (
    train_disease_model,
)

from epidemiological_intelligence.modeling.predict import (
    predict_models,
)

from epidemiological_intelligence.modeling.evaluate import (
    compare_models,
    metrics_by_municipality,
)

from epidemiological_intelligence.artifacts.results import (
    save_metrics,
    save_predictions,
    save_municipality_metrics,
)


def run_disease_pipeline(
    df: pd.DataFrame,
    disease: str,
):

    if disease not in MODEL_CONFIG:
        raise ValueError(
            f"Doença não configurada: {disease}"
        )

    # ------------------------------
    # 1. Preparação
    # ------------------------------

    model_df = prepare_model_data(df)

    # ------------------------------
    # 2. Feature engineering
    # ------------------------------

    model_df = create_climate_lags(
        model_df
    )

    selected_features = (
        MODEL_CONFIG[disease]["features"]
    )

    # ------------------------------
    # 3. Split temporal
    # ------------------------------

    cutoff = pd.Timestamp(TEST_START)

    train_df = model_df[
        model_df["reference_date"] < cutoff
    ].copy()

    test_df = model_df[
        model_df["reference_date"] >= cutoff
    ].copy()

    # ------------------------------
    # 4. Treinamento
    # ------------------------------

    model_result = train_disease_model(
        train_df=train_df,
        test_df=test_df,
        disease=disease,
        selected_features=selected_features,
    )

    # ------------------------------
    # 5. Previsão
    # ------------------------------

    predictions = predict_models(
        base_model=model_result.base_model,
        final_model=model_result.final_model,
        df=model_result.test_df,
    )

    # ------------------------------
    # 6. Avaliação global
    # ------------------------------

    comparison = compare_models(
        y_true=predictions["cases"],
        base_pred=predictions[
            "base_prediction"
        ],
        final_pred=predictions[
            "final_prediction"
        ],
    )

    # ------------------------------
    # 7. Avaliação por município
    # ------------------------------

    municipality_metrics = (
        metrics_by_municipality(
            test_df=predictions,
            prediction_column=(
                "final_prediction"
            ),
        )
    )

    # ------------------------------
    # 8. Salvar artefatos
    # ------------------------------

    save_metrics(
        disease=disease,
        metrics=comparison,
    )

    save_predictions(
        disease=disease,
        predictions=predictions,
    )

    save_municipality_metrics(
        disease=disease,
        municipality_metrics=(
            municipality_metrics
        ),
    )

    # ------------------------------
    # 9. Retorno
    # ------------------------------

    return {
        "disease": disease,
        "selected_features": (
            selected_features
        ),
        "model_result": model_result,
        "predictions": predictions,
        "comparison": comparison,
        "municipality_metrics": (
            municipality_metrics
        ),
    }