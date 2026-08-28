import pandas as pd

from epidemiological_intelligence.features.lags import create_climate_lags


def test_create_climate_lags_shifts_within_municipality(sample_gold_df):
    result = create_climate_lags(sample_gold_df)

    muni_a = (
        result[result["municipality"] == "MUNI_A"]
        .sort_values("reference_date")
        .reset_index(drop=True)
    )

    # first observation has no prior month -> lag1 is NaN
    assert pd.isna(muni_a.loc[0, "precipitation_sum_mm_lag1"])

    # lag1 of month N equals precipitation_sum_mm of month N-1
    raw_values = muni_a["precipitation_sum_mm"].tolist()
    lag1_values = muni_a["precipitation_sum_mm_lag1"].tolist()
    assert lag1_values[1:] == raw_values[:-1]


def test_create_climate_lags_does_not_leak_across_municipalities(sample_gold_df):
    result = create_climate_lags(sample_gold_df)

    muni_b_first_row = (
        result[result["municipality"] == "MUNI_B"]
        .sort_values("reference_date")
        .iloc[0]
    )

    # MUNI_B's first row must not inherit MUNI_A's last value as a lag
    assert pd.isna(muni_b_first_row["precipitation_sum_mm_lag1"])

    # the fixture uses non-overlapping value ranges per municipality, so any
    # leak would show up as a MUNI_A value appearing in MUNI_B's lag column
    muni_a_raw_values = set(
        result[result["municipality"] == "MUNI_A"]["precipitation_sum_mm"]
    )
    muni_b_lag_values = set(
        result[result["municipality"] == "MUNI_B"]["precipitation_sum_mm_lag1"].dropna()
    )
    assert muni_a_raw_values.isdisjoint(muni_b_lag_values)


def test_create_climate_lags_preserves_row_count_with_multiple_diseases(sample_gold_df):
    # Gold has one row per (municipality, month, disease); climate columns
    # repeat across diseases for the same municipality/month. The dedup step
    # in create_climate_lags must not drop or multiply epidemiological rows.
    other_disease_df = sample_gold_df.copy()
    other_disease_df["disease"] = "ASMA"
    combined = pd.concat([sample_gold_df, other_disease_df], ignore_index=True)

    result = create_climate_lags(combined)

    assert len(result) == len(combined)


def test_create_climate_lags_generates_configured_lag_columns(sample_gold_df):
    result = create_climate_lags(sample_gold_df, lags=(1, 2))

    assert "precipitation_sum_mm_lag1" in result.columns
    assert "precipitation_sum_mm_lag2" in result.columns
    assert "precipitation_sum_mm_lag3" not in result.columns
