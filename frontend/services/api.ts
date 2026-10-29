import type { ChatRequest, ChatResponse } from "@/types/chat";
import type {
  CaseCurvePoint,
  OverviewMetrics,
} from "@/types/epidemiology";
import type {
  EpidemiologicalDataFilters,
  EpidemiologicalRecord,
  MunicipalityOption,
} from "@/types/data";
import type { GeoArea, MapLevel } from "@/types/map";
import type {
  AlertFilters,
  AlertModelInfo,
  AlertRecord,
  AlertStateSummary,
} from "@/types/alert";

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
    // 429 (limite de requisições do chat) e 404 do alerta (job ainda não
    // rodou) trazem uma mensagem pronta para o usuário em `detail` -- ver
    // ai/src/epidemiological_agent/api/.
    if (response.status === 404 || response.status === 429) {
      const body = await response.json().catch(() => null);
      if (typeof body?.detail === "string") {
        throw new ApiError(body.detail, response.status);
      }
    }

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
 */
export function sendChatMessage(payload: ChatRequest) {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Wire shapes for the routes below -- narrower than the frontend types
 * in types/, since the API doesn't (and shouldn't) know about
 * presentation-only fields like a disease's Portuguese label or a
 * study's hand-written description. Each *Service.ts merges these
 * with local presentation data (lib/constants.ts) into the full type.
 */

export interface ApiDiseaseDistributionSlice {
  disease: string;
  cases: number;
  shareOfTotalPct: number;
}

export interface ApiOverviewResponse {
  metrics: OverviewMetrics;
  caseCurve: CaseCurvePoint[];
  diseaseDistribution: ApiDiseaseDistributionSlice[];
}

export interface ApiStudySummary {
  disease: string;
  totalCases: number;
  municipalityCount: number;
  statesInAlert: number | null;
  maxAlertProbability: number | null;
}

export interface OverviewFilters {
  diseases?: string[];
  startDate?: string;
  endDate?: string;
}

/** Maps 1:1 to GET /overview?disease=&start_date=&end_date=. */
export function getOverview(filters: OverviewFilters = {}) {
  const params = new URLSearchParams();
  for (const disease of filters.diseases ?? []) {
    params.append("disease", disease);
  }
  if (filters.startDate) params.set("start_date", filters.startDate);
  if (filters.endDate) params.set("end_date", filters.endDate);

  const query = params.toString();
  return request<ApiOverviewResponse>(`/overview${query ? `?${query}` : ""}`);
}

/** Maps 1:1 to GET /geo/{level}?state=&disease=&start_date=&end_date=. */
export function getGeo(level: MapLevel, state?: string, filters: OverviewFilters = {}) {
  const params = new URLSearchParams();
  if (state) params.set("state", state);
  for (const disease of filters.diseases ?? []) {
    params.append("disease", disease);
  }
  if (filters.startDate) params.set("start_date", filters.startDate);
  if (filters.endDate) params.set("end_date", filters.endDate);

  const query = params.toString();
  return request<GeoArea[]>(`/geo/${level}${query ? `?${query}` : ""}`);
}

/** Maps 1:1 to GET /studies. */
export function getStudiesData() {
  return request<ApiStudySummary[]>("/studies");
}

/** Maps 1:1 to GET /alerts?level=&origin_type=&disease=&state=&municipality_code=&horizon=&only_alerts=&limit=. */
export function getAlerts(filters: AlertFilters = {}) {
  const params = new URLSearchParams();
  if (filters.level) params.set("level", filters.level);
  if (filters.originType) params.set("origin_type", filters.originType);
  if (filters.disease) params.set("disease", filters.disease);
  if (filters.state) params.set("state", filters.state);
  if (filters.municipalityCode) params.set("municipality_code", filters.municipalityCode);
  if (filters.horizon) params.set("horizon", String(filters.horizon));
  if (filters.onlyAlerts) params.set("only_alerts", "true");
  if (filters.limit) params.set("limit", String(filters.limit));

  const query = params.toString();
  return request<AlertRecord[]>(`/alerts${query ? `?${query}` : ""}`);
}

/** Maps 1:1 to GET /alerts/states?origin_type=&horizon=&disease=. */
export function getAlertStates(originType: string, horizon: number, disease?: string) {
  const params = new URLSearchParams({ origin_type: originType, horizon: String(horizon) });
  if (disease) params.set("disease", disease);
  return request<AlertStateSummary[]>(`/alerts/states?${params.toString()}`);
}

/** Maps 1:1 to GET /alerts/model (404 before the alert job's first run). */
export function getAlertModel() {
  return request<AlertModelInfo>("/alerts/model");
}

/** Maps 1:1 to GET /municipalities?state=. */
export function getMunicipalitiesData(state?: string) {
  const query = state ? `?state=${encodeURIComponent(state)}` : "";
  return request<MunicipalityOption[]>(`/municipalities${query}`);
}

/** Maps 1:1 to GET /data?disease=&state=&municipality_code=&start_date=&end_date=. */
export function getEpidemiologicalData(filters: EpidemiologicalDataFilters) {
  const params = new URLSearchParams();
  if (filters.disease) params.set("disease", filters.disease);
  if (filters.state) params.set("state", filters.state);
  if (filters.municipalityCode) params.set("municipality_code", filters.municipalityCode);
  if (filters.startDate) params.set("start_date", filters.startDate);
  if (filters.endDate) params.set("end_date", filters.endDate);

  const query = params.toString();
  return request<EpidemiologicalRecord[]>(`/data${query ? `?${query}` : ""}`);
}
