import pandas as pd
from fastapi import APIRouter, Query

from epidemiological_agent.api.schemas_data import EpidemiologicalRecord
from epidemiological_agent.api.schemas_geo import MunicipalityOption
from epidemiological_agent.tools import gold_queries
from epidemiological_agent.tools.bigquery_tools import CLIMATE_COLUMNS, query_epidemiological_data

router = APIRouter(tags=["data"])


def _none_if_nan(value) -> float | None:
    # pd.isna() covers None, float NaN, and pandas' own NA marker
    # (pd.NA -- what a nullable-dtype column actually holds).
    # math.isnan(pd.NA) raises TypeError; returning pd.NA unchanged made
    # Pydantic reject it as "not a valid float" -- a 500 on any row
    # with a missing value.
    if pd.isna(value):
        return None
    return float(value)


def _none_if_missing(value) -> str | None:
    return None if value is None or pd.isna(value) else str(value)


@router.get("/data", response_model=list[EpidemiologicalRecord])
def get_data(
    disease: str | None = Query(default=None),
    state: str | None = Query(default=None),
    municipality_code: str | None = Query(default=None),
    municipality: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> list[EpidemiologicalRecord]:
    """
    Registros mensais para Explorar Dados e o painel de cada estudo.
    Com município: as linhas dele. Sem: casos somados e clima médio por
    mês, na UF filtrada ou no Brasil (ver query_epidemiological_data).
    """

    df = query_epidemiological_data(
        disease=disease,
        municipality=municipality,
        start_date=start_date,
        end_date=end_date,
        state=state,
        municipality_code=municipality_code,
    )

    return [
        EpidemiologicalRecord(
            reference_date=pd.Timestamp(row.reference_date).date().isoformat(),
            disease=row.disease,
            municipality=row.municipality,
            state=_none_if_missing(getattr(row, "state", None)),
            municipality_code=_none_if_missing(getattr(row, "municipality_code", None)),
            cases=_none_if_nan(row.cases),
            **{
                column: _none_if_nan(getattr(row, column))
                for column in CLIMATE_COLUMNS
            },
        )
        for row in df.itertuples()
    ]


@router.get("/municipalities", response_model=list[MunicipalityOption])
def get_municipalities(state: str | None = Query(default=None)) -> list[MunicipalityOption]:
    """
    Municípios do IBGE (código de 6 dígitos, nome, UF) para os seletores
    do frontend -- por código, já que o nome sozinho tem homônimos.
    """

    df = gold_queries.municipalities(state)

    return [
        MunicipalityOption(code=row.municipality_code, name=row.municipality_name, state=row.state)
        for row in df.itertuples()
    ]
