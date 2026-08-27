import json

from langchain_core.tools import tool
from google.api_core.exceptions import GoogleAPIError

from epidemiological_agent.tools.model_tools import (
    get_model_metrics,
    get_predictions,
    get_municipality_metrics
)

from epidemiological_agent.tools.bigquery_tools import (
    query_epidemiological_data,
    get_total_cases
)
from epidemiological_agent.rag.vector_store import (
    search_knowledge,
)
from epidemiological_agent.tools.tool_errors import (
    tool_error_response,
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

    Includes baseline and final model metrics such as
    MAE, RMSE, R2 and WAPE.
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
        return tool_error_response(
            source="gcs",
            error_type="artifact_not_found",
            message=(
                f"Não foram encontrados artefatos "
                f"do modelo para {disease}."
            ),
        )

    except GoogleAPIError:
        return tool_error_response(
            source="gcs",
            error_type="storage_unavailable",
            message=(
                "Não foi possível acessar os artefatos "
                "do modelo no GCS."
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
    Return the total observed number of cases using SUM(cases).

    ALWAYS use this tool when the user asks for the total
    number of observed cases in a period.
    """

    try:
        total = get_total_cases(
            disease=disease,
            municipality=municipality,
            start_date=start_date,
            end_date=end_date,
        )

        return str(total)

    except Exception:
        return tool_error_response(
            source="bigquery",
            error_type="query_failed",
            message=(
                "Não foi possível consultar o total de casos "
                "no BigQuery."
            ),
        )

@tool
def retrieve_knowledge_tool(
    query: str,
) -> str:
    """
    Search the project knowledge base.

    Use this tool for questions about:
    - modeling methodology
    - statistical metrics
    - Negative Binomial regression
    - model limitations
    - data leakage
    - lags
    - interpretation of predictions
    - association versus causality
    - project modeling decisions
    """

    try:
        docs = search_knowledge(
            query=query,
            k=2,
        )

        if not docs:
            return json.dumps(
                {
                    "status": "not_found",
                    "message": (
                        "Nenhum conteúdo metodológico relevante "
                        "foi encontrado."
                    ),
                },
                ensure_ascii=False,
            )

        return "\n\n---\n\n".join(
            doc.page_content
            for doc in docs
        )

    except Exception:
        return tool_error_response(
            source="rag",
            error_type="retrieval_failed",
            message=(
                "Não foi possível consultar "
                "a base de conhecimento."
            ),
        )