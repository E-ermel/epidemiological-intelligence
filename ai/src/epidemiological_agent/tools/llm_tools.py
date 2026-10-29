import json
import logging
import pandas as pd
from langchain_core.tools import tool
from google.api_core.exceptions import GoogleAPIError

from epidemiological_agent.tools import alert_queries, gold_queries

from epidemiological_agent.tools.bigquery_tools import (
    query_epidemiological_data,
    get_total_cases,
    get_climate_summary,
    get_max_reference_date,
)
from epidemiological_agent.rag.vector_store import (
    search_knowledge,
)
from epidemiological_agent.tools.tool_errors import (
    tool_error_response,
)

logger = logging.getLogger(__name__)


def _date_range_out_of_bounds_response(start_date: str | None) -> str | None:
    """
    Structured error when `start_date` is later than the most recent
    reference_date the project has, so callers can tell the user data
    only goes so far (e.g. a request for 2026) instead of reporting a
    plain, unexplained "no data found" for a future period.
    """

    if start_date is None:
        return None

    max_date = get_max_reference_date()

    if max_date is None:
        return None

    try:
        requested_start = pd.Timestamp(start_date)
    except (ValueError, TypeError):
        return None

    if requested_start.date() <= max_date.date():
        return None

    return tool_error_response(
        source="bigquery",
        error_type="date_out_of_range",
        message=(
            f"Não há dados disponíveis a partir de {start_date}. "
            "Os registros do projeto vão até "
            f"{max_date.date().isoformat()}."
        ),
    )

@tool
def epidemiological_data_tool(
    disease: str,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    state: str | None = None,
) -> str:
    """
    Return detailed monthly epidemiological and climate records.

    Use this tool when the user asks for:
    - monthly values
    - time series
    - climate variables
    - detailed historical records

    DO NOT use this tool when the user only asks for
    the total number of cases. Use total_cases_tool instead.

    Coverage is all of Brazil. `state` is the two-letter UF code
    (e.g. "RS", "SP"). Pass it together with `municipality` whenever
    the state is known: municipality names repeat across states (Santa
    Maria exists in RS and RN). Without `municipality`, records come
    aggregated per month for the state (or for Brazil, without state).
    """
    out_of_bounds = _date_range_out_of_bounds_response(start_date)

    if out_of_bounds is not None:
        return out_of_bounds

    df = query_epidemiological_data(
        disease=disease,
        municipality=municipality,
        start_date=start_date,
        end_date=end_date,
        state=state,
    )
    
    if df.empty:
        return "No data found for the requested filters."

    return df.to_json(
        orient="records",
        date_format="iso",
    )
    
@tool
def outbreak_alerts_tool(
    disease: str | None = None,
    state: str | None = None,
    municipality: str | None = None,
    origin_type: str = "fechado",
    only_alerts: bool = True,
) -> str:
    """
    Return the outbreak alert of the latest monthly run: for each
    series, the probability of an outbreak 1, 2 and 3 months ahead,
    whether it crossed the alert cutoff, and the expected cases
    (p10, median, p90) against the endemic channel threshold.

    Use this tool when the user asks about outbreak alerts, outbreak
    risk, "surto", "alerta", or what is expected for the next months.

    - Without `municipality`, returns the state (UF) level alert.
    - With `municipality`, pass `state` too (names repeat across states).
    - `origin_type`: "fechado" (forecast from the last month with
      complete data, the default and more reliable) or "provisorio"
      (from the latest month, whose data is still incomplete).
    - `only_alerts=False` also returns series below the cutoff.

    An outbreak here means cases above the endemic channel (mean + 1.96
    standard deviations of the same month in the previous 5 years) and
    at least 5 cases in a state or 3 in a municipality.
    """

    if origin_type not in alert_queries.ORIGIN_TYPES:
        origin_type = "fechado"

    municipality_code = None
    if municipality:
        options = gold_queries.municipalities(state)
        target = gold_queries.normalize_name(municipality)
        matches = options[options["municipality_name"].map(gold_queries.normalize_name) == target]
        if matches.empty:
            return f"Municipality not found: {municipality}" + (f" ({state})" if state else "") + "."
        if len(matches) > 1:
            return (
                f"{municipality} exists in more than one state "
                f"({', '.join(sorted(matches['state']))}); pass `state`."
            )
        municipality_code = matches["municipality_code"].iloc[0]

    try:
        df = alert_queries.latest_alerts(
            alert_queries.AlertFilters(
                level="municipio" if municipality_code else "uf",
                origin_type=origin_type,
                disease=disease,
                state=state,
                municipality_code=municipality_code,
                only_alerts=only_alerts,
            ),
            limit=60,
        )
    except GoogleAPIError:
        logger.exception("BigQuery query failed in outbreak_alerts_tool")
        return tool_error_response(
            source="bigquery",
            error_type="alerts_unavailable",
            message="Não foi possível consultar os alertas de surto.",
        )

    if df.empty:
        if municipality_code:
            return (
                "No alert rows for this municipality: either nothing is above the cutoff, or the series "
                "has too few cases (municipal alerts need >= 1 case/month on average; the state alert "
                "still covers it)."
            )
        return "No outbreak alerts for the requested filters in the latest run."

    columns = [
        "origin_type", "origin_month", "disease", "state", "municipality_name", "target_month", "horizon",
        "probability", "alert", "threshold", "cases_p10", "cases_p50", "cases_p90", "observed_cases",
    ]
    numeric = ["probability", "threshold", "cases_p10", "cases_p50", "cases_p90", "observed_cases"]
    return df[columns].round(dict.fromkeys(numeric, 3)).to_json(orient="records", date_format="iso", force_ascii=False)


@tool
def alert_model_info_tool() -> str:
    """
    Return how the outbreak alert model works and how well it did on
    the 2024-2025 test: model, covariates, alert cutoffs, precision,
    recall, F1, AUC and the origin months of the latest run.

    Use this tool when the user asks how reliable the alerts are,
    which model is used, or for its metrics.
    """

    try:
        info = alert_queries.model_info()
    except GoogleAPIError:
        logger.exception("Failed to read alert model info in GCS")
        return tool_error_response(
            source="gcs",
            error_type="storage_unavailable",
            message="Não foi possível acessar as informações do modelo de alerta.",
        )

    if info is None:
        return tool_error_response(
            source="gcs",
            error_type="artifact_not_found",
            message="O alerta de surtos ainda não foi gerado.",
        )

    return json.dumps(info, ensure_ascii=False)


@tool
def total_cases_tool(
    disease: str,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    state: str | None = None,
) -> str:
    """
    Return the total number of observed cases for a disease.

    Use this tool when the user asks:
    - how many cases occurred;
    - total cases;
    - cumulative cases;
    - total cases for a municipality;
    - total cases within a specific date range.

    Prefer this tool over epidemiological_data_tool when
    only the aggregated total is required.

    `state` (two-letter UF code) restricts the total to one state, and
    disambiguates `municipality` names that exist in several states.
    """

    out_of_bounds = _date_range_out_of_bounds_response(start_date)

    if out_of_bounds is not None:
        return out_of_bounds

    try:
        total = get_total_cases(
            disease=disease,
            municipality=municipality,
            start_date=start_date,
            end_date=end_date,
            state=state,
        )

        return str(total)

    except Exception:
        logger.exception(
            (
                "BigQuery query failed in total_cases_tool | "
                "disease=%s | municipality=%s"
            ),
            disease,
            municipality,
        )

        return tool_error_response(
            source="bigquery",
            error_type="query_failed",
            message=(
                "Não foi possível consultar o total "
                "de casos no BigQuery."
            ),
        )
@tool
def climate_summary_tool(
    disease: str | None = None,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    state: str | None = None,
) -> str:
    """
    Return aggregated climate statistics -- average, minimum, and
    maximum -- for precipitation, temperature, dew point, humidity,
    atmospheric pressure, and wind, over the matching period.

    Use this tool when the user asks about climate/weather conditions
    (e.g. average rainfall, how hot it was, wind speed in a
    municipality), especially when they want an aggregate
    (average/typical/highest/lowest) rather than a full monthly time
    series. `disease`, `municipality` and `state` (two-letter UF code)
    are all optional.

    DO NOT use this tool for case counts; use total_cases_tool or
    epidemiological_data_tool instead.
    """

    out_of_bounds = _date_range_out_of_bounds_response(start_date)

    if out_of_bounds is not None:
        return out_of_bounds

    try:
        summary = get_climate_summary(
            disease=disease,
            municipality=municipality,
            start_date=start_date,
            end_date=end_date,
            state=state,
        )

        return json.dumps(
            summary,
            ensure_ascii=False,
        )

    except Exception:
        logger.exception(
            (
                "BigQuery query failed in climate_summary_tool | "
                "disease=%s | municipality=%s"
            ),
            disease,
            municipality,
        )

        return tool_error_response(
            source="bigquery",
            error_type="query_failed",
            message=(
                "Não foi possível consultar os dados "
                "climáticos no BigQuery."
            ),
        )


@tool
def retrieve_knowledge_tool(
    query: str,
) -> str:
    """
    Search the project's methodological knowledge base.

    Use this tool for questions about:
    - modeling methodology;
    - Negative Binomial regression;
    - MAE, RMSE, R2 and WAPE definitions;
    - statistical interpretation;
    - model limitations;
    - lags and temporal features;
    - data leakage;
    - association versus causality;
    - project modeling decisions.

    Do not use this tool to retrieve actual numerical
    model metrics or historical epidemiological values.
    """

    try:
        docs = search_knowledge(
            query=query,
            k=2,
        )

        if not docs:
            logger.info(
                "No RAG documents found for query"
            )

            return json.dumps(
                {
                    "status": "not_found",
                    "source": "rag",
                    "message": (
                        "Nenhum conteúdo metodológico "
                        "relevante foi encontrado."
                    ),
                },
                ensure_ascii=False,
            )

        return "\n\n---\n\n".join(
            doc.page_content
            for doc in docs
        )

    except Exception:
        logger.exception(
            "RAG retrieval failed"
        )

        return tool_error_response(
            source="rag",
            error_type="retrieval_failed",
            message=(
                "Não foi possível consultar "
                "a base de conhecimento."
            ),
        )