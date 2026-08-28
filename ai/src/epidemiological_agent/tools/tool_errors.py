import json


def tool_error_response(
    source: str,
    error_type: str,
    message: str,
) -> str:
    """
    Padroniza respostas de erro das tools.

    A ideia é impedir que cada tool retorne erros
    em um formato diferente.
    """

    return json.dumps(
        {
            "status": "error",
            "source": source,
            "error_type": error_type,
            "message": message,
        },
        ensure_ascii=False,
    )