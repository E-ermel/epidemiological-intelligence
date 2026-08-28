from fastapi import APIRouter, Query

from epidemiological_agent.api.gold_data import load_gold_dataframe
from epidemiological_agent.api.schemas_geo import GeoArea

router = APIRouter(tags=["geo"])

# Only Rio Grande do Sul has real pipeline data today (DE/DS only
# process RS sources). The rest render neutral/disabled on the
# country-level map until more states are onboarded -- same
# limitation the frontend mock already documented, just backed by a
# real RS number now instead of a hardcoded one.
KNOWN_STATES: dict[str, str] = {
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "PR": "Paraná",
    "SP": "São Paulo",
    "RJ": "Rio de Janeiro",
    "MG": "Minas Gerais",
}


@router.get("/geo/{level}", response_model=list[GeoArea])
def get_geo(
    level: str,
    state: str | None = Query(default=None),
) -> list[GeoArea]:
    df = load_gold_dataframe()

    if level == "country":
        total_cases = int(df["cases"].sum(skipna=True))

        return [
            GeoArea(
                id=code,
                name=name,
                cases=total_cases if code == "RS" else 0,
                has_data=code == "RS",
            )
            for code, name in KNOWN_STATES.items()
        ]

    if level == "state" and state == "RS":
        totals = df.groupby("municipality")["cases"].sum(skipna=True)

        return [
            GeoArea(
                id=municipality,
                name=municipality.title(),
                cases=int(cases),
                has_data=True,
            )
            for municipality, cases in totals.items()
        ]

    return []
