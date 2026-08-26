import pandas as pd


def predict_cases(
    model,
    df: pd.DataFrame,
    prediction_column: str = "prediction",
) -> pd.DataFrame:

    result = df.copy()

    result[prediction_column] = model.predict(
        result
    )

    return result

def predict_models(
    base_model,
    final_model,
    df: pd.DataFrame,
) -> pd.DataFrame:

    result = df.copy()

    result["base_prediction"] = (
        base_model.predict(result)
    )

    result["final_prediction"] = (
        final_model.predict(result)
    )

    return result