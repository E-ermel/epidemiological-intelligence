/**
 * Outbreak alert, mirrors GET /alerts, /alerts/states and /alerts/model
 * (ai/src/epidemiological_agent/api/routers/alerts.py). Each monthly run
 * forecasts from two origins per disease:
 * - "fechado": the last month with complete data (default, more reliable);
 * - "provisorio": the latest month, whose data is still incomplete.
 */
export type AlertOriginType = "fechado" | "provisorio";
export type AlertLevel = "uf" | "municipio";

export interface AlertRecord {
  originType: AlertOriginType;
  originMonth: string;
  level: AlertLevel;
  disease: string;
  source: string;
  state: string;
  municipalityCode: string | null;
  municipalityName: string | null;
  targetMonth: string;
  horizon: number;
  /** Endemic channel limit: cases above it (and above a minimum) are an outbreak. */
  threshold: number;
  casesP10: number;
  casesP50: number;
  casesP90: number;
  probability: number;
  cutoff: number;
  alert: boolean;
  /** Cases already reported for the target month (null if not yet known). */
  observedCases: number | null;
  targetProvisional: boolean | null;
}

export interface AlertStateSummary {
  state: string;
  name: string;
  maxProbability: number | null;
  stateAlerts: number;
  municipalityAlerts: number;
}

export interface AlertLevelMetrics {
  precision: number;
  recall: number;
  f1: number;
  aucPr: number;
  aucRoc: number;
  brier: number;
  testPredictions: number;
  outbreakPct: number;
}

export interface AlertModelInfo {
  runId: string;
  modelVersion: string;
  modelName: string;
  covariates: string[];
  horizons: number[];
  cutoffs: Record<AlertLevel, number>;
  testMetrics: Record<AlertLevel, AlertLevelMetrics>;
  origins: { originType: AlertOriginType; disease: string; originMonth: string }[];
}

export interface AlertFilters {
  level?: AlertLevel;
  originType?: AlertOriginType;
  disease?: string;
  state?: string;
  municipalityCode?: string;
  horizon?: number;
  onlyAlerts?: boolean;
  limit?: number;
}
