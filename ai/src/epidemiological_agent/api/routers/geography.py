from dataclasses import replace

import pandas as pd
from fastapi import APIRouter, Query

from epidemiological_agent.tools import gold_queries
from epidemiological_agent.tools.gold_queries import STATE_NAMES, GoldFilters
from epidemiological_agent.api.schemas_geo import GeoArea

router = APIRouter(tags=["geo"])


@router.get("/geo/{level}", response_model=list[GeoArea])
def get_geo(
    level: str,
    state: str | None = Query(default=None),
    disease: list[str] = Query(default=[]),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> list[GeoArea]:
    filters = GoldFilters(diseases=tuple(disease), start_date=start_date, end_date=end_date)

    if level == "country":
        # As 27 UFs sempre, mesmo sem caso no filtro: o mapa desenha todas.
        cases = gold_queries.cases_by_state(filters).set_index("state")["cases"]

        return [
            GeoArea(
                id=code,
                name=name,
                cases=int(cases.get(code, 0)),
                has_data=code in cases.index,
            )
            for code, name in STATE_NAMES.items()
        ]

    if level == "state" and state:
        municipalities = gold_queries.cases_by_municipality(replace(filters, state=state))

        return [
            GeoArea(
                id=row.municipality_code,
                name=row.municipality_name,
                cases=int(row.cases),
                has_data=True,
                latitude=None if pd.isna(row.latitude) else float(row.latitude),
                longitude=None if pd.isna(row.longitude) else float(row.longitude),
            )
            for row in municipalities.itertuples()
        ]

    return []
