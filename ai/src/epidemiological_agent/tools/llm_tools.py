import json
import logging
import pandas as pd
from langchain_core.tools import tool
from google.api_core.exceptions import GoogleAPIError

from epidemiological_agent.tools.model_tools import (
    get_model_metrics,
    get_predictions,
    get_municipality_metrics
)

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
    """
    out_of_bounds = _date_range_out_of_bounds_response(start_date)

    if out_of_bounds is not None:
        return out_of_bounds

    df = query_epidemiological_data(
        disease=disease,
        municipality=municipality,
        start_date=start_date,
        end_date=end_date,
    )
    
    if df.empty:
        return "No data found for the requested filters."

    return df.to_json(
        orient="records",
        date_format="iso",
    )
    
@tool
def model_metrics_tool(
    disease: str,
) -> str:
    """
    Return evaluation metrics for a disease model.

    Use this tool when the user asks for actual model
    performance metrics such as MAE, RMSE, R2, WAPE,
    or comparison between baseline and final model.
    """

    try:
        metrics = get_model_metrics(
            disease
        )

        return json.dumps(
            metrics,
            ensure_ascii=False,
        )

    except FileNotFoundError:
        logger.warning(
            "Model metrics artifact not found | disease=%s",
            disease,
        )

        return tool_error_response(
            source="gcs",
            error_type="artifact_not_found",
            message=(
                f"Não foram encontrados artefatos "
                f"do modelo para {disease}."
            ),
        )

    except GoogleAPIError:
        logger.exception(
            "Failed to access model metrics in GCS | disease=%s",
            disease,
        )

        return tool_error_response(
            source="gcs",
            error_type="storage_unavailable",
            message=(
                "Não foi possível acessar os artefatos "
                "dos modelos no GCS."
            ),
        )
        
@tool
def municipality_model_metrics_tool(
    disease: str,
    municipality: str,
) -> str:
    """
    Return model performance metrics for a specific municipality.
    """

    df = get_municipality_metrics(
        disease
    )

    result = df[
        df["municipality"] == municipality
    ]

    if result.empty:
        return (
            f"No model metrics found for "
            f"{municipality} and {disease}."
        )

    return result.to_json(
        orient="records",
    )
    
@tool
def model_predictions_tool(
    disease: str,
    municipality: str | None = None,
) -> str:
    """
    Return observed versus predicted case counts for a disease.
    """

    df = get_predictions(
        disease
    )

    if municipality is not None:
        df = df[
            df["municipality"] == municipality
        ]

    if df.empty:
        return "No predictions found."

    return df.to_json(
        orient="records",
        date_format="iso",
    )

@tool
def total_cases_tool(
    disease: str,
    municipality: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
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
) -> str:
    """
    Return aggregated climate statistics -- average, minimum, and
    maximum -- for precipitation, temperature, dew point, humidity,
    atmospheric pressure, and wind, over the matching period.

    Use this tool when the user asks about climate/weather conditions
    (e.g. average rainfall, how hot it was, wind speed in a
    municipality), especially when they want an aggregate
    (average/typical/highest/lowest) rather than a full monthly time
    series. `disease` and `municipality` are both optional.

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