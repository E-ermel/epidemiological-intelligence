import numpy as np
import pandas as pd

from epidemiological_intelligence.data.preparation import prepare_model_data


def test_prepare_model_data_parses_reference_date_and_month():
    df = pd.DataFrame(
        {
            "disease": ["LEPTOSPIROSE", "LEPTOSPIROSE"],
            "municipality": ["MUNI_A", "MUNI_A"],
            "reference_date": ["2024-03-01", "2024-01-01"],
            "cases": [10, 5],
        }
    )

    result = prepare_model_data(df)

    assert pd.api.types.is_datetime64_any_dtype(result["reference_date"])
    assert result["reference_date"].dt.tz is None
    # sorted chronologically -> January comes before March
    assert result["month"].tolist() == [1, 3]


def test_prepare_model_data_sorts_by_disease_municipality_and_date():
    df = pd.DataFrame(
        {
            "disease": ["B", "A", "A"],
            "municipality": ["Z", "Y", "Y"],
            "reference_date": ["2024-02-01", "2024-02-01", "2024-01-01"],
            "cases": [1, 2, 3],
        }
    )

    result = prepare_model_data(df)

    assert result["disease"].tolist() == ["A", "A", "B"]
    assert result["reference_date"].tolist() == list(
        pd.to_datetime(["2024-01-01", "2024-02-01", "2024-02-01"])
    )


def test_prepare_model_data_coerces_invalid_cases_to_nan():
    df = pd.DataFrame(
        {
            "disease": ["LEPTOSPIROSE"],
            "municipality": ["MUNI_A"],
            "reference_date": ["2024-01-01"],
            "cases": ["not-a-number"],
        }
    )

    result = prepare_model_data(df)

    assert np.isnan(result["cases"].iloc[0])


def test_prepare_model_data_strips_timezone_from_bigquery_timestamps():
    # BigQuery TIMESTAMP columns come back as tz-aware (UTC); the rest of
    # the pipeline (e.g. run_modeling's naive pd.Timestamp(TEST_START) cutoff)
    # assumes naive datetimes.
    df = pd.DataFrame(
        {
            "disease": ["LEPTOSPIROSE"],
            "municipality": ["MUNI_A"],
            "reference_date": pd.to_datetime(["2024-01-01"]).tz_localize("UTC"),
            "cases": [1],
        }
    )

    result = prepare_model_data(df)

    assert result["reference_date"].dt.tz is None


def test_prepare_model_data_is_idempotent_on_already_naive_dates():
    df = pd.DataFrame(
        {
            "disease": ["LEPTOSPIROSE"],
            "municipality": ["MUNI_A"],
            "reference_date": ["2024-01-01"],
            "cases": [1],
        }
    )

    result = prepare_model_data(df)

    assert result["reference_date"].dt.tz is None
