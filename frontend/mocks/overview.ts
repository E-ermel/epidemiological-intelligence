import type {
  CaseCurvePoint,
  DiseaseDistributionSlice,
  OverviewMetrics,
} from "@/types/epidemiology";
import { DISEASES } from "@/lib/constants";

/**
 * MOCK DATA. query_epidemiological_data / get_total_cases
 * (ai/src/epidemiological_agent/tools/bigquery_tools.py) already do
 * this aggregation, but only as agent tools reachable through
 * POST /chat -- there is no plain HTTP endpoint for the UI to call.
 * TODO: backend endpoint required (e.g. GET /overview).
 */

export const MOCK_OVERVIEW_METRICS: OverviewMetrics = {
  totalCases: 118_620,
  totalCasesTrendPct: 6.4,
  municipalityCount: 148,
  diseaseCount: DISEASES.length,
  periodStart: "2019-01-01",
  periodEnd: "2024-12-01",
};

function monthsBetween(start: string, count: number): string[] {
  const startDate = new Date(start);
  return Array.from({ length: count }, (_, i) => {
    const date = new Date(startDate);
    date.setMonth(date.getMonth() + i);
    return date.toISOString().slice(0, 10);
  });
}

export const MOCK_CASE_CURVE: CaseCurvePoint[] = monthsBetween(
  "2023-01-01",
  24
).map((referenceDate, i) => {
  const seasonal = Math.sin((i / 12) * Math.PI * 2) * 320;
  const trend = i * 18;
  const base = 1450 + seasonal + trend;
  return { referenceDate, cases: Math.max(400, Math.round(base)) };
});

export const MOCK_DISEASE_DISTRIBUTION: DiseaseDistributionSlice[] = [
  { disease: "ASMA", label: "Asma", cases: 34_210, shareOfTotalPct: 28.8 },
  { disease: "BRONQUITE AGUDA", label: "Bronquite Aguda", cases: 27_640, shareOfTotalPct: 23.3 },
  { disease: "LEPTOSPIROSE", label: "Leptospirose", cases: 21_980, shareOfTotalPct: 18.5 },
  {
    disease: "INSUFICIÊNCIA CARDÍACA",
    label: "Insuficiência Cardíaca",
    cases: 15_340,
    shareOfTotalPct: 12.9,
  },
  {
    disease: "INFARTO AGUDO DO MIOCÁRDIO",
    label: "Infarto Agudo do Miocárdio",
    cases: 11_760,
    shareOfTotalPct: 9.9,
  },
  {
    disease: "BRONQUITE CRÔNICA",
    label: "Bronquite Crônica",
    cases: 7_690,
    shareOfTotalPct: 6.5,
  },
];
