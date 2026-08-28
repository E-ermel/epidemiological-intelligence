import type { ChatRequest, ChatResponse } from "@/types/chat";

/**
 * Single source of truth for the FastAPI base URL. Never hardcode a
 * host in a component -- import the functions in this file instead.
 */
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8080";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Não foi possível conectar à API. Verifique se o backend está no ar e se NEXT_PUBLIC_API_URL está configurado."
    );
  }

  if (!response.ok) {
    throw new ApiError(
      `A API retornou um erro (${response.status}).`,
      response.status
    );
  }

  return response.json() as Promise<T>;
}

/**
 * Maps 1:1 to GET / in ai/src/epidemiological_agent/api/app.py.
 */
export function getServiceInfo() {
  return request<{ service: string; status: string; docs: string; health: string }>(
    "/"
  );
}

/**
 * Maps 1:1 to GET /health in ai/src/epidemiological_agent/api/app.py.
 */
export function getHealth() {
  return request<{ status: string }>("/health");
}

/**
 * Maps 1:1 to POST /chat in ai/src/epidemiological_agent/api/app.py.
 * This is the only endpoint in this file that isn't a mock -- it calls
 * the real LangGraph agent.
 *
 * Known limitation: the FastAPI app does not configure CORS
 * (no CORSMiddleware in api/app.py), so calling this from a browser
 * origin other than the API's own will currently fail. Needs a backend
 * change before this works end-to-end outside of same-origin setups.
 */
export function sendChatMessage(payload: ChatRequest) {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
