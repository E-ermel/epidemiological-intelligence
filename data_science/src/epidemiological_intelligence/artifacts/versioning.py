import re
import unicodedata

from epidemiological_intelligence.artifacts.storage import (
    get_storage_client,
    get_storage_config,
)


_VERSION_PATTERN = re.compile(r"^v(\d+)$")


def disease_to_slug(disease: str) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        disease,
    )

    ascii_name = normalized.encode(
        "ascii",
        "ignore",
    ).decode("ascii")

    slug = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        ascii_name,
    )

    return slug.strip("_").lower()


def get_next_version(
    disease: str,
) -> str:
    _, bucket_name, artifact_prefix = (
        get_storage_config()
    )

    client = get_storage_client()
    bucket = client.bucket(bucket_name)

    disease_slug = disease_to_slug(disease)

    disease_prefix = (
        f"{artifact_prefix.rstrip('/')}/"
        f"{disease_slug}/"
    )

    blobs = client.list_blobs(
        bucket,
        prefix=disease_prefix,
    )

    versions = set()

    for blob in blobs:
        relative_path = blob.name[
            len(disease_prefix):
        ]

        first_part = relative_path.split("/", 1)[0]

        match = _VERSION_PATTERN.match(first_part)

        if match:
            versions.add(
                int(match.group(1))
            )

    if not versions:
        return "v1"

    return f"v{max(versions) + 1}"