"""
AIH reduzida (RD) -> internações por doença, município e mês.

Critérios validados contra a exportação manual do TabNet (RS, 2024,
100% das células município × mês iguais):

- diagnóstico principal (DIAG_PRINC) nos grupos de CID-10 da Lista de
  Morbidade do TabNet;
- só AIH normal (IDENT = 1): a de longa permanência (5) é continuação
  de uma internação já contada;
- mês da internação (DT_INTER), não a competência de processamento --
  uma internação aparece na competência em que a AIH foi aprovada,
  às vezes meses depois.

Os dois municípios são mantidos: o de residência do paciente
(MUNIC_RES, contagem principal) e o de internação, onde fica o hospital
(MUNIC_MOV) -- o TabNet exportado usava este último.
"""

import pandas as pd

RAW_COLUMNS = ["MUNIC_RES", "MUNIC_MOV", "DIAG_PRINC", "DT_INTER", "IDENT"]

# Prefixos de CID-10 (3 ou 4 caracteres, sem ponto, como no SIH).
DISEASE_CID_PREFIXES = {
    "ASMA": ("J45", "J46"),
    "BRONQUITE AGUDA": ("J20", "J21"),
    "BRONQUITE CRÔNICA": ("J40", "J41", "J42", "J43", "J44"),
    "INFARTO AGUDO DO MIOCÁRDIO": ("I21", "I22"),
    "INSUFICIÊNCIA CARDÍACA": ("I50",),
    # A93.0, febre do Oropouche. Quase só zeros antes de 2024.
    "OROPOUCHE": ("A930",),
}

SILVER_COLUMNS = [
    "disease",
    "residence_municipality_code",
    "occurrence_municipality_code",
    "year",
    "month",
    "hospitalizations",
]

GROUP_KEYS = SILVER_COLUMNS[:-1]


def classify_disease(diagnosis: pd.Series) -> pd.Series:
    """Nome da doença de cada CID, ou NA se não pertence a nenhum grupo."""

    disease = pd.Series(pd.NA, index=diagnosis.index, dtype="object")

    for name, prefixes in DISEASE_CID_PREFIXES.items():
        disease = disease.mask(diagnosis.str.startswith(prefixes), name)

    return disease


def aggregate_hospitalizations(records: pd.DataFrame, first_year: int) -> pd.DataFrame:
    """
    Registros RD (RAW_COLUMNS, como texto) -> contagem por doença,
    residência, internação e mês da internação.

    Internações antes de `first_year` saem: estão em competências que
    não foram baixadas, então a contagem desses meses viria incompleta.
    """

    df = records[records["IDENT"] == "1"]
    df = df.assign(disease=classify_disease(df["DIAG_PRINC"]))
    df = df[df["disease"].notna()]

    df = df.assign(
        residence_municipality_code=df["MUNIC_RES"],
        occurrence_municipality_code=df["MUNIC_MOV"],
        year=pd.to_numeric(df["DT_INTER"].str[:4], errors="coerce"),
        month=pd.to_numeric(df["DT_INTER"].str[4:6], errors="coerce"),
    )
    df = df[df["year"].ge(first_year) & df["month"].between(1, 12)]

    return (
        df.groupby(GROUP_KEYS, as_index=False)
        .size()
        .rename(columns={"size": "hospitalizations"})
        .astype({"year": "int64", "month": "int64", "hospitalizations": "int64"})
    )[SILVER_COLUMNS]


def mark_provisional(
    silver: pd.DataFrame,
    latest_competencia: tuple[int, int],
    provisional_months: int,
) -> pd.DataFrame:
    """
    is_provisional = mês de internação a menos de `provisional_months`
    da última competência publicada: AIHs desses meses ainda chegam.
    """

    latest_year, latest_month = latest_competencia
    latest_index = latest_year * 12 + latest_month
    month_index = silver["year"] * 12 + silver["month"]

    return silver.assign(is_provisional=month_index > latest_index - provisional_months)


def combine(aggregates: list[pd.DataFrame]) -> pd.DataFrame:
    """Soma agregados de vários arquivos: a mesma internação-mês chega em várias competências."""

    if not aggregates:
        return pd.DataFrame(columns=SILVER_COLUMNS)

    return (
        pd.concat(aggregates, ignore_index=True)
        .groupby(GROUP_KEYS, as_index=False)["hospitalizations"]
        .sum()
    )[SILVER_COLUMNS]
