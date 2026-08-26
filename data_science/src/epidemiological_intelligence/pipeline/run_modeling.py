from epidemiological_intelligence.data.preparation import (
    prepare_model_data,
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
    df,
    disease,
    selected_features,
):
    # 1. Preparação
    df = prepare_model_data(df)

    # 2. Split temporal
    train_df = df[
        df["reference_date"] < "2024-01-01"
    ].copy()

    test_df = df[
        df["reference_date"] >= "2024-01-01"
    ].copy()

    # 3. Treinamento
    result = train_disease_model(
        train_df=train_df,
        test_df=test_df,
        disease=disease,
        selected_features=selected_features,
    )

    # 4. Previsões
    predictions = predict_models(
        base_model=result.base_model,
        final_model=result.final_model,
        df=result.test_df,
    )

    # 5. Avaliação
    comparison = compare_models(
        y_true=predictions["cases"],
        base_pred=predictions["base_prediction"],
        final_pred=predictions["final_prediction"],
    )

    municipality_metrics = metrics_by_municipality(
        test_df=predictions,
        prediction_column="final_prediction",
    )

    # 6. Salvar artefatos
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
        municipality_metrics=municipality_metrics,
    )

    return {
        "model_result": result,
        "predictions": predictions,
        "comparison": comparison,
        "municipality_metrics": municipality_metrics,
    }