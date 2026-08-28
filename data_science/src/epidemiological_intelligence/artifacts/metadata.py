from datetime import datetime, timezone
from typing import Any


def build_model_metadata(
    *,
    disease: str,
    version: str,
    selected_features: list[str],
    comparison: dict[str, Any],
    train_start,
    train_end,
    test_start,
    test_end,
) -> dict[str, Any]:

    trained_at = datetime.now(timezone.utc)

    run_id = trained_at.strftime(
        "%Y%m%dT%H%M%SZ"
    )

    return {
        "disease": disease,
        "model_version": version,
        "run_id": run_id,
        "trained_at": trained_at.isoformat(),
        "model_type": "Negative Binomial",
        "features": list(selected_features),
        "training_period": {
            "start": str(train_start),
            "end": str(train_end),
        },
        "test_period": {
            "start": str(test_start),
            "end": str(test_end),
        },
        "metrics": comparison,
    }