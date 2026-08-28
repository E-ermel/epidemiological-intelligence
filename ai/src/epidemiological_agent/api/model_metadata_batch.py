from concurrent.futures import ThreadPoolExecutor

from epidemiological_agent.tools.model_tools import get_model_metadata


def fetch_model_metadata_for_diseases(diseases) -> dict[str, dict | None]:
    """
    get_model_metadata() per disease is a real GCS round trip each --
    /models and /studies both need it for every disease in the Gold
    table, and running that in a sequential for-loop (6 diseases today)
    was the single biggest contributor to those routes' latency.
    They're independent reads, so run them concurrently instead.

    Returns {disease: metadata} for diseases with a trained model, and
    {disease: None} for ones that don't (FileNotFoundError) -- callers
    decide what to do with a None (skip it, or report "sem modelo").
    """

    def _fetch(disease: str) -> tuple[str, dict | None]:
        try:
            return disease, get_model_metadata(disease)
        except FileNotFoundError:
            return disease, None

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(diseases)))) as executor:
        results = executor.map(_fetch, diseases)

    return dict(results)
