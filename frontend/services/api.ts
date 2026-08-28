import type { ChatRequest, ChatResponse } from "@/types/chat";
import type {
  CaseCurvePoint,
  OverviewMetrics,
} from "@/types/epidemiology";
import type { EpidemiologicalDataFilters, EpidemiologicalRecord } from "@/types/data";
import type { GeoArea, MapLevel } from "@/types/map";
import type { ModelMetadata, ObservedVsPredictedPoint } from "@/types/model";

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
  activeModelVersion: string | null;
}

/** Maps 1:1 to GET /overview. */
export function getOverview() {
  return request<ApiOverviewResponse>("/overview");
}

/** Maps 1:1 to GET /geo/{level}?state=. */
export function getGeo(level: MapLevel, state?: string) {
  const query = state ? `?state=${encodeURIComponent(state)}` : "";
  return request<GeoArea[]>(`/geo/${level}${query}`);
}

/** Maps 1:1 to GET /studies. */
export function getStudiesData() {
  return request<ApiStudySummary[]>("/studies");
}

/** Maps 1:1 to GET /models. */
export function getModelsData() {
  return request<ModelMetadata[]>("/models");
}

/** Maps 1:1 to GET /models/{disease}/predictions?municipality=. */
export function getModelPredictions(disease: string, municipality?: string) {
  const query = municipality
    ? `?municipality=${encodeURIComponent(municipality)}`
    : "";
  return request<ObservedVsPredictedPoint[]>(
    `/models/${encodeURIComponent(disease)}/predictions${query}`
  );
}

/** Maps 1:1 to GET /data?disease=&municipality=&start_date=&end_date=. */
export function getEpidemiologicalData(filters: EpidemiologicalDataFilters) {
  const params = new URLSearchParams();
  if (filters.disease) params.set("disease", filters.disease);
  if (filters.municipality) params.set("municipality", filters.municipality);
  if (filters.startDate) params.set("start_date", filters.startDate);
  if (filters.endDate) params.set("end_date", filters.endDate);

  const query = params.toString();
  return request<EpidemiologicalRecord[]>(`/data${query ? `?${query}` : ""}`);
}
