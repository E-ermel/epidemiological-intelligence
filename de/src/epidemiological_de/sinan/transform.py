"""
Fichas do SINAN -> casos por doença, município e mês.

Dois municípios por caso, como no SIH: o de residência (contagem
principal) e o do evento -- o provável de infecção na leptospirose e o
do acidente nos peçonhentos. O do evento costuma vir em branco quando a
investigação não o apurou; aí o caso conta só na residência.

O mês é o do evento (primeiros sintomas; data do acidente), o mais
perto da exposição. A exportação manual do TabNet usava município e mês
de notificação.
"""

import pandas as pd

LEPT_COLUMNS = ["ID_MN_RESI", "COMUNINF", "DT_SIN_PRI", "CLASSI_FIN"]
ANIM_COLUMNS = ["ID_MN_RESI", "ANT_MUNIC_", "ANT_DT_ACI", "DT_SIN_PRI", "TP_ACIDENT"]

RAW_COLUMNS = {"LEPT": LEPT_COLUMNS, "ANIM": ANIM_COLUMNS}

# TP_ACIDENT da ficha de acidentes por animais peçonhentos. Cada tipo
# tem relação diferente com o clima (o escorpionismo é urbano e sazonal,
# o ofidismo é rural), então vira uma "doença" própria.
VENOMOUS_ANIMALS = {
    "1": "ACIDENTE POR SERPENTE",
    "2": "ACIDENTE POR ARANHA",
    "3": "ACIDENTE POR ESCORPIÃO",
    "4": "ACIDENTE POR LAGARTA",
    "5": "ACIDENTE POR ABELHA",
}
OTHER_VENOMOUS = "ACIDENTE POR OUTRO ANIMAL PEÇONHENTO"  # 6 = outros, 9/branco = ignorado

LEPTOSPIROSIS = "LEPTOSPIROSE"
CONFIRMED = "1"

SILVER_COLUMNS = [
    "disease",
    "residence_municipality_code",
    "occurrence_municipality_code",
    "year",
    "month",
    "cases",
]

GROUP_KEYS = SILVER_COLUMNS[:-1]


def _blank_to_na(series: pd.Series) -> pd.Series:
    return series.mask(series.fillna("").str.strip() == "", pd.NA)


def leptospirosis_events(records: pd.DataFrame) -> pd.DataFrame:
    """Só casos confirmados (CLASSI_FIN = 1), como no TabNet."""

    df = records[records["CLASSI_FIN"] == CONFIRMED]

    return pd.DataFrame(
        {
            "disease": LEPTOSPIROSIS,
            "residence_municipality_code": _blank_to_na(df["ID_MN_RESI"]),
            "occurrence_municipality_code": _blank_to_na(df["COMUNINF"]),
            "event_date": df["DT_SIN_PRI"],
        }
    )


def venomous_accident_events(records: pd.DataFrame) -> pd.DataFrame:
    """Toda notificação conta (a ficha não tem classificação final)."""

    accident_date = _blank_to_na(records["ANT_DT_ACI"]).fillna(records["DT_SIN_PRI"])

    return pd.DataFrame(
        {
            "disease": records["TP_ACIDENT"].map(VENOMOUS_ANIMALS).fillna(OTHER_VENOMOUS),
            "residence_municipality_code": _blank_to_na(records["ID_MN_RESI"]),
            "occurrence_municipality_code": _blank_to_na(records["ANT_MUNIC_"]),
            "event_date": accident_date,
        }
    )


EVENT_BUILDERS = {"LEPT": leptospirosis_events, "ANIM": venomous_accident_events}


def aggregate_cases(events: pd.DataFrame, first_year: int) -> pd.DataFrame:
    """
    Eventos -> contagem por doença, residência, local do evento e mês.
    Eventos antes de `first_year` saem: estão em arquivos que não foram
    baixados, então esses meses viriam incompletos.
    """

    df = events.assign(
        year=pd.to_numeric(events["event_date"].str[:4], errors="coerce"),
        month=pd.to_numeric(events["event_date"].str[4:6], errors="coerce"),
    )
    df = df[df["year"].ge(first_year) & df["month"].between(1, 12)]

    # dropna=False: caso sem local do evento ainda conta na residência.
    return (
        df.groupby(GROUP_KEYS, as_index=False, dropna=False)
        .size()
        .rename(columns={"size": "cases"})
        .astype({"year": "int64", "month": "int64", "cases": "int64"})
    )[SILVER_COLUMNS]


def mark_provisional(silver: pd.DataFrame, preliminary_years: set[int]) -> pd.DataFrame:
    """is_provisional = ano cuja base o DATASUS ainda publica como preliminar (PRELIM)."""

    return silver.assign(is_provisional=silver["year"].isin(preliminary_years))


def combine(aggregates: list[pd.DataFrame]) -> pd.DataFrame:
    """Soma agregados de vários anos: um caso de dezembro pode ser notificado em janeiro."""

    if not aggregates:
        return pd.DataFrame(columns=SILVER_COLUMNS)

    return (
        pd.concat(aggregates, ignore_index=True)
        .groupby(GROUP_KEYS, as_index=False, dropna=False)["cases"]
        .sum()
    )[SILVER_COLUMNS]
