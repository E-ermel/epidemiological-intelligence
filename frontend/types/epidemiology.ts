/**
 * Disease codes as stored in the Gold table and used by MODEL_CONFIG
 * (data_science/src/epidemiological_intelligence/modeling/configs.py).
 */
export type DiseaseCode =
  | "ASMA"
  | "BRONQUITE AGUDA"
  | "BRONQUITE CRÔNICA"
  | "INFARTO AGUDO DO MIOCÁRDIO"
  | "INSUFICIÊNCIA CARDÍACA"
  | "LEPTOSPIROSE";

export interface OverviewMetrics {
  totalCases: number;
  totalCasesTrendPct: number | null;
  municipalityCount: number;
  diseaseCount: number;
  periodStart: string;
  periodEnd: string;
}

export interface CaseCurvePoint {
  referenceDate: string;
  cases: number;
}

export interface DiseaseDistributionSlice {
  disease: DiseaseCode;
  label: string;
  cases: number;
  shareOfTotalPct: number;
}
