import type {
  CaseCurvePoint,
  DiseaseCode,
  DiseaseDistributionSlice,
  OverviewMetrics,
} from "@/types/epidemiology";
import { getOverview, type OverviewFilters } from "@/services/api";
import { DISEASE_LABELS } from "@/lib/constants";

export interface OverviewData {
  metrics: OverviewMetrics;
  caseCurve: CaseCurvePoint[];
  diseaseDistribution: DiseaseDistributionSlice[];
}

export async function getOverviewData(filters: OverviewFilters = {}): Promise<OverviewData> {
  const response = await getOverview(filters);

  return {
    metrics: response.metrics,
    caseCurve: response.caseCurve,
    diseaseDistribution: response.diseaseDistribution.map((slice) => {
      const disease = slice.disease as DiseaseCode;
      return {
        ...slice,
        disease,
        label: DISEASE_LABELS[disease] ?? slice.disease,
      };
    }),
  };
}
