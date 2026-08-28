from epidemiological_agent.api.schemas_base import CamelModel


class GeoArea(CamelModel):
    id: str
    name: str
    cases: int
    has_data: bool
