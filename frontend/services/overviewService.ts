import type {
  CaseCurvePoint,
  DiseaseDistributionSlice,
  OverviewMetrics,
} from "@/types/epidemiology";
import {
  MOCK_CASE_CURVE,
  MOCK_DISEASE_DISTRIBUTION,
  MOCK_OVERVIEW_METRICS,
} from "@/mocks/overview";

/**
 * TODO: backend endpoint required. Replace the mock reads below with
 * calls through services/api.ts (e.g. request<OverviewMetrics>("/overview"))
 * once that endpoint exists -- pages/components call these functions,
 * not the mocks directly, so that swap won't touch any component.
 */

export async function getOverviewMetrics(): Promise<OverviewMetrics> {
  return MOCK_OVERVIEW_METRICS;
}

export async function getCaseCurve(): Promise<CaseCurvePoint[]> {
  return MOCK_CASE_CURVE;
}

export async function getDiseaseDistribution(): Promise<DiseaseDistributionSlice[]> {
  return MOCK_DISEASE_DISTRIBUTION;
}
