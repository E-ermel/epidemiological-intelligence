from epidemiological_agent.api.schemas_base import CamelModel


class GeoArea(CamelModel):
    """
    `id` é a sigla da UF (nível country) ou o código de 6 dígitos do
    município (nível state). latitude/longitude (centróide do IBGE) só
    vêm no nível state, para o mapa posicionar cada município.
    """

    id: str
    name: str
    cases: int
    has_data: bool
    latitude: float | None = None
    longitude: float | None = None


class MunicipalityOption(CamelModel):
    code: str
    name: str
    state: str
