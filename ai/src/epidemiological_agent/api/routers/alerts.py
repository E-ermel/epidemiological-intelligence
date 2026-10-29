import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from epidemiological_agent.api.schemas_alerts import (
    AlertModelInfo,
    AlertRecord,
    AlertStateSummary,
)
from epidemiological_agent.tools import alert_queries
from epidemiological_agent.tools.alert_queries import AlertFilters
from epidemiological_agent.tools.gold_queries import STATE_NAMES

router = APIRouter(tags=["alerts"])


def _date(value) -> str:
    return pd.Timestamp(value).date().isoformat()


def _number(value) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


def _check(level: str | None = None, origin_type: str | None = None) -> None:
    if level is not None and level not in alert_queries.LEVELS:
        raise HTTPException(status_code=422, detail=f"level deve ser um de {alert_queries.LEVELS}")
    if origin_type is not None and origin_type not in alert_queries.ORIGIN_TYPES:
        raise HTTPException(status_code=422, detail=f"origin_type deve ser um de {alert_queries.ORIGIN_TYPES}")


@router.get("/alerts", response_model=list[AlertRecord])
def get_alerts(
    level: str = Query(default="uf"),
    origin_type: str = Query(default="fechado"),
    disease: str | None = Query(default=None),
    state: str | None = Query(default=None),
    municipality_code: str | None = Query(default=None),
    horizon: int | None = Query(default=None, ge=1, le=3),
    only_alerts: bool = Query(default=False),
    limit: int = Query(default=500, ge=1, le=alert_queries.MAX_ROWS),
) -> list[AlertRecord]:
    _check(level, origin_type)
    df = alert_queries.latest_alerts(
        AlertFilters(
            level=level,
            origin_type=origin_type,
            disease=disease,
            state=state,
            municipality_code=municipality_code,
            horizon=horizon,
            only_alerts=only_alerts,
        ),
        limit=limit,
    )

    return [
        AlertRecord(
            origin_type=row.origin_type,
            origin_month=_date(row.origin_month),
            level=row.level,
            disease=row.disease,
            source=row.source,
            state=row.state,
            municipality_code=row.municipality_code if isinstance(row.municipality_code, str) else None,
            municipality_name=row.municipality_name if isinstance(row.municipality_name, str) else None,
            target_month=_date(row.target_month),
            horizon=int(row.horizon),
            threshold=float(row.threshold),
            cases_p10=float(row.cases_p10),
            cases_p50=float(row.cases_p50),
            cases_p90=float(row.cases_p90),
            probability=float(row.probability),
            cutoff=float(row.cutoff),
            alert=bool(row.alert),
            observed_cases=_number(row.observed_cases),
            target_provisional=None if pd.isna(row.target_provisional) else bool(row.target_provisional),
        )
        for row in df.itertuples()
    ]


@router.get("/alerts/states", response_model=list[AlertStateSummary])
def get_alert_states(
    origin_type: str = Query(default="fechado"),
    horizon: int = Query(default=1, ge=1, le=3),
    disease: str | None = Query(default=None),
) -> list[AlertStateSummary]:
    _check(origin_type=origin_type)
    df = alert_queries.state_summary(origin_type, horizon, disease)

    return [
        AlertStateSummary(
            state=row.state,
            name=STATE_NAMES.get(row.state, row.state),
            max_probability=_number(row.max_probability),
            state_alerts=int(row.state_alerts),
            municipality_alerts=int(row.municipality_alerts),
        )
        for row in df.itertuples()
    ]


@router.get("/alerts/model", response_model=AlertModelInfo)
def get_alert_model() -> AlertModelInfo:
    info = alert_queries.model_info()
    if info is None:
        raise HTTPException(status_code=404, detail="O job do alerta ainda não rodou.")

    return AlertModelInfo(
        run_id=info["run_id"],
        model_version=info["model_version"],
        model_name=info["model"]["name"],
        covariates=info["model"]["covariates"],
        horizons=info["model"]["horizons"],
        cutoffs=info["cutoffs"],
        test_metrics=info["test_metrics"],
        origins=info["origins"],
    )
