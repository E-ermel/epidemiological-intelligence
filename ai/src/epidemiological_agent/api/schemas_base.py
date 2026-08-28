from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """
    Base for response models that are new UI-facing shapes (not a
    direct mirror of a GCS/BigQuery artifact) -- serializes as
    camelCase to match the existing frontend/types/*.ts field names.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
