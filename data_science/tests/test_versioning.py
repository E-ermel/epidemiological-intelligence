import pytest

from epidemiological_intelligence.artifacts.versioning import (
    disease_to_slug,
    get_next_version,
)


@pytest.mark.parametrize(
    "disease, expected_slug",
    [
        ("INSUFICIÊNCIA CARDÍACA", "insuficiencia_cardiaca"),
        ("BRONQUITE AGUDA", "bronquite_aguda"),
        ("BRONQUITE CRÔNICA", "bronquite_cronica"),
        ("INFARTO AGUDO DO MIOCÁRDIO", "infarto_agudo_do_miocardio"),
        ("LEPTOSPIROSE", "leptospirose"),
        ("ASMA", "asma"),
    ],
)
def test_disease_to_slug_normalizes_accents_and_spaces(disease, expected_slug):
    assert disease_to_slug(disease) == expected_slug


def test_get_next_version_returns_v1_when_no_versions_exist(fake_storage):
    assert get_next_version("LEPTOSPIROSE") == "v1"


def test_get_next_version_returns_v2_when_v1_exists(fake_storage):
    fake_storage.objects["modeling/leptospirose/v1/metadata.json"] = b"{}"

    assert get_next_version("LEPTOSPIROSE") == "v2"


def test_get_next_version_uses_the_highest_existing_version(fake_storage):
    fake_storage.objects["modeling/leptospirose/v1/metadata.json"] = b"{}"
    fake_storage.objects["modeling/leptospirose/v2/metadata.json"] = b"{}"
    fake_storage.objects["modeling/leptospirose/v5/metadata.json"] = b"{}"

    assert get_next_version("LEPTOSPIROSE") == "v6"


def test_get_next_version_ignores_objects_that_are_not_version_folders(fake_storage):
    fake_storage.objects["modeling/leptospirose/latest.json"] = b"{}"
    fake_storage.objects["modeling/leptospirose/metrics.json"] = b"{}"
    fake_storage.objects["modeling/leptospirose/vFinal/metadata.json"] = b"{}"
    fake_storage.objects["modeling/leptospirose/v1/metadata.json"] = b"{}"

    assert get_next_version("LEPTOSPIROSE") == "v2"


def test_get_next_version_is_scoped_per_disease(fake_storage):
    fake_storage.objects["modeling/asma/v1/metadata.json"] = b"{}"
    fake_storage.objects["modeling/asma/v2/metadata.json"] = b"{}"

    assert get_next_version("LEPTOSPIROSE") == "v1"
