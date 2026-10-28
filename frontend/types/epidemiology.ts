/**
 * Disease codes as stored in the Gold table -- set by the DE pipeline
 * in de/src/epidemiological_de/sih/transform.py (hospitalizations) and
 * de/src/epidemiological_de/sinan/transform.py (notifications).
 */
export type DiseaseCode =
  | "ASMA"
  | "BRONQUITE AGUDA"
  | "BRONQUITE CRÔNICA"
  | "INFARTO AGUDO DO MIOCÁRDIO"
  | "INSUFICIÊNCIA CARDÍACA"
  | "OROPOUCHE"
  | "LEPTOSPIROSE"
  | "ACIDENTE POR ESCORPIÃO"
  | "ACIDENTE POR SERPENTE"
  | "ACIDENTE POR ARANHA"
  | "ACIDENTE POR ABELHA"
  | "ACIDENTE POR LAGARTA"
  | "ACIDENTE POR OUTRO ANIMAL PEÇONHENTO";

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
