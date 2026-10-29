import numpy as np
import pandas as pd
import pytest

from epidemiological_intelligence.alert import config, forecast, prepare, publish
from epidemiological_intelligence.alert.run import run

MONTHS = pd.date_range("2015-01-01", "2021-06-01", freq="MS")


def make_gold(sinan_partial_last=True):
    """2 municípios do RS, ASMA (SIH) e LEPTOSPIROSE (SINAN), jan/2015 a jun/2021."""

    rng = np.random.default_rng(0)
    rows = []
    for disease, source, level in [("ASMA", "SIH", 8.0), ("LEPTOSPIROSE", "SINAN", 6.0)]:
        for code, scale in [("430010", 1.0), ("430020", 0.1)]:
            for ds in MONTHS:
                if source == "SIH" and ds == MONTHS[-1]:
                    continue  # SIH termina um mês antes
                cases = rng.poisson(level * scale)
                if source == "SINAN" and sinan_partial_last and ds == MONTHS[-1]:
                    cases = 0.0  # mês em andamento
                provisional = ds >= pd.Timestamp("2021-04-01") if source == "SIH" else ds.year == 2021
                rows.append((disease, source, code, "RS", ds, float(cases), provisional))
    cases = pd.DataFrame(
        rows, columns=["disease", "source", "municipality_code", "state", "ds", "cases", "is_provisional"]
    )
    # Garante o mês parcial do SINAN com algum caso (> 0) mas < metade.
    sinan_last = (cases["source"] == "SINAN") & (cases["ds"] == MONTHS[-1]) & (cases["municipality_code"] == "430010")
    cases.loc[sinan_last, "cases"] = 1.0 if sinan_partial_last else cases.loc[sinan_last, "cases"]

    context = pd.DataFrame(
        [(code, "RS", ds, 1000.0 if code == "430010" else 100.0, 100.0, 20.0, 18.0, 80.0)
         for code in ("430010", "430020") for ds in MONTHS],
        columns=["municipality_code", "state", "ds", "population", *config.CLIMATE],
    )
    context.loc[5, "temperature_avg_c"] = np.nan  # buraco de clima
    return cases, context


def fake_forecaster(history):
    """Quantis em torno do último valor de cada série: q(nível) = último × 2 × nível."""

    ids = np.sort(history["series_id"].unique())
    last = history.sort_values("ds").groupby("series_id")["y"].last().reindex(ids).to_numpy()
    levels = np.array(config.QUANTILE_LEVELS)
    q = last[:, None, None] * 2 * levels[None, None, :] * np.ones((1, len(config.HORIZONS), 1))
    return ids, q


def test_source_origins_follow_completeness_rule():
    cases, _ = make_gold()
    origins = prepare.source_origins(cases).set_index(["source", "origin_type"])["origin"]

    # SIH: último mês com dados = mai/2021; fechado = último sem provisório (mar/2021).
    assert origins[("SIH", "provisorio")] == pd.Timestamp("2021-05-01")
    assert origins[("SIH", "fechado")] == pd.Timestamp("2021-03-01")
    # SINAN: jun/2021 em andamento sai do provisório; fechado = 2 meses antes do último com dados.
    assert origins[("SINAN", "provisorio")] == pd.Timestamp("2021-05-01")
    assert origins[("SINAN", "fechado")] == pd.Timestamp("2021-04-01")


def test_complete_last_month_stays_provisional_origin():
    cases, _ = make_gold(sinan_partial_last=False)
    cases.loc[(cases["source"] == "SINAN") & (cases["ds"] == MONTHS[-1]), "cases"] = 5.0
    origins = prepare.source_origins(cases).set_index(["source", "origin_type"])["origin"]
    assert origins[("SINAN", "provisorio")] == MONTHS[-1]


def test_eligible_series_need_one_case_per_month():
    cases, _ = make_gold()
    eligible = prepare.eligible_municipal_series(cases, prepare.disease_origins(cases))
    pairs = set(map(tuple, eligible.astype(str).to_numpy()))
    assert ("ASMA", "430010") in pairs  # ~8/mês
    assert ("LEPTOSPIROSE", "430010") in pairs  # ~6/mês
    assert ("ASMA", "430020") not in pairs  # ~0,8/mês


def test_endemic_channel_uses_same_month_of_previous_five_years():
    months = pd.date_range("2015-01-01", "2021-12-01", freq="MS")
    panel = pd.DataFrame({"series_id": "X|RS", "ds": months, "y": np.arange(len(months), dtype=float)})
    panel.loc[panel["ds"] > "2021-06-01", "y"] = np.nan  # meses previstos
    out = prepare.endemic_channel(panel, "uf").set_index("ds")

    past = np.array([0, 12, 24, 36, 48], dtype=float) + 12  # jan/2016..jan/2020 -> índices 12..60
    jan_2021 = out.loc["2021-01-01"]
    assert jan_2021["channel_mean"] == pytest.approx(past.mean())
    assert jan_2021["threshold"] == pytest.approx(past.mean() + 1.96 * past.std(ddof=1))
    assert not np.isnan(out.loc["2021-09-01", "threshold"])  # mês previsto também tem limite
    assert np.isnan(out.loc["2019-01-01", "threshold"])  # sem 5 anos


def test_sih_channel_skips_pandemic_years_and_sinan_does_not():
    months = pd.date_range("2015-01-01", "2023-01-01", freq="MS")
    rows = []
    for disease, source in [("ASMA", "SIH"), ("LEPTOSPIROSE", "SINAN")]:
        for ds in months:
            y = 0.0 if ds.year in (2020, 2021) else float(ds.year - 2000)  # pandemia derruba os casos
            rows.append((f"{disease}|RS", source, ds, y))
    panel = pd.DataFrame(rows, columns=["series_id", "source", "ds", "y"])
    out = prepare.endemic_channel(panel, "uf").set_index(["series_id", "ds"])

    # jan/2023, SIH: 2022, 2019, 2018, 2017, 2016 (pula 2020-2021).
    sih = np.array([22, 19, 18, 17, 16], dtype=float)
    assert out.loc[("ASMA|RS", pd.Timestamp("2023-01-01")), "channel_mean"] == pytest.approx(sih.mean())
    # SINAN: 2022, 2021, 2020, 2019, 2018 (canal normal).
    sinan = np.array([22, 0, 0, 19, 18], dtype=float)
    assert out.loc[("LEPTOSPIROSE|RS", pd.Timestamp("2023-01-01")), "channel_sd"] == pytest.approx(sinan.std(ddof=1))


def test_exceed_probability_interpolates_cdf():
    levels = np.array(config.QUANTILE_LEVELS)
    quantiles = np.vstack([levels * 100, levels * 100])
    p = forecast.exceed_probability(quantiles, np.array([50.0, 1000.0]))
    assert p[0] == pytest.approx(0.5)
    assert p[1] == 0.0


def test_run_end_to_end_with_fake_forecaster():
    cases, context = make_gold()
    alerts = run(cases, context, fake_forecaster, ["uf", "municipio"])

    assert set(alerts["origin_type"]) == {"fechado", "provisorio"}
    assert set(alerts["level"]) == {"uf", "municipio"}
    assert set(alerts["horizon"]) == {1, 2, 3}
    assert alerts["municipality_code"][alerts["level"] == "uf"].isna().all()
    assert alerts["probability"].between(0, 1).all()
    assert (alerts["alert"] == (alerts["probability"] >= alerts["cutoff"])).all()

    asma_closed = alerts[(alerts["disease"] == "ASMA") & (alerts["origin_type"] == "fechado")]
    assert set(asma_closed["target_month"]) == {pd.Timestamp("2021-04-01"), pd.Timestamp("2021-05-01"),
                                                pd.Timestamp("2021-06-01")}
    # Alvo de abr/2021 já tem casos (provisórios); jun/2021 ainda não.
    uf = asma_closed[asma_closed["level"] == "uf"].set_index("target_month")
    assert uf.loc["2021-04-01", "target_provisional"]
    assert np.isnan(uf.loc["2021-06-01", "observed_cases"])

    alerts["run_id"] = pd.Timestamp("2021-07-10", tz="UTC")
    alerts["model_version"] = config.MODEL_VERSION
    meta = publish.summary(alerts, alerts["run_id"].iloc[0])
    assert meta["cutoffs"] == config.CUTOFFS
    assert {o["origin_type"] for o in meta["origins"]} == {"fechado", "provisorio"}


def test_origin_override_is_used_for_every_disease():
    cases, context = make_gold()
    alerts = run(cases, context, fake_forecaster, ["uf"], origin=pd.Timestamp("2020-12-01"))
    assert set(alerts["origin_month"]) == {pd.Timestamp("2020-12-01")}
