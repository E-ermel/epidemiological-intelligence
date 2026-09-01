import type { DiseaseCode } from "@/types/epidemiology";
import type { EpidemiologicalRecord } from "@/types/data";

export const APP_NAME = "Epidemiological Intelligence";
export const APP_SUBTITLE = "Plataforma de Inteligência Epidemiológica";

export const NAV_ITEMS = [
  { label: "Visão Geral", href: "/" },
  { label: "Estudos", href: "/estudos" },
  { label: "Explorar Dados", href: "/dados" },
  { label: "Modelos", href: "/modelos" },
  { label: "Agente IA", href: "/agente" },
] as const;

/**
 * Mirrors MODEL_CONFIG in
 * data_science/src/epidemiological_intelligence/modeling/configs.py.
 * Keep in sync with the backend -- this is the authoritative list of
 * diseases the pipeline actually models.
 */
export const DISEASES: { code: DiseaseCode; label: string }[] = [
  { code: "ASMA", label: "Asma" },
  { code: "BRONQUITE AGUDA", label: "Bronquite Aguda" },
  { code: "BRONQUITE CRÔNICA", label: "Bronquite Crônica" },
  { code: "INFARTO AGUDO DO MIOCÁRDIO", label: "Infarto Agudo do Miocárdio" },
  { code: "INSUFICIÊNCIA CARDÍACA", label: "Insuficiência Cardíaca" },
  { code: "LEPTOSPIROSE", label: "Leptospirose" },
];

export const DISEASE_LABELS: Record<DiseaseCode, string> = Object.fromEntries(
  DISEASES.map((d) => [d.code, d.label])
) as Record<DiseaseCode, string>;

/**
 * One color per disease, reused everywhere a disease needs a visual
 * identity (DiseaseDistributionChart) so the
 * same disease reads as the same color across the app. Deliberately
 * all cool/blue-adjacent hues (blue, cyan, indigo, teal, violet, sky)
 * -- distinguishable without breaking the "predominância de azul, sem
 * neon" design language.
 */
export const DISEASE_COLORS: Record<DiseaseCode, string> = {
  ASMA: "#2563eb",
  "BRONQUITE AGUDA": "#0891b2",
  "BRONQUITE CRÔNICA": "#4f46e5",
  "INFARTO AGUDO DO MIOCÁRDIO": "#0d9488",
  "INSUFICIÊNCIA CARDÍACA": "#7c3aed",
  LEPTOSPIROSE: "#0369a1",
};

/**
 * Presentation-only copy -- the API has no business generating prose,
 * so this stays client-side, keyed by the real `disease` code the
 * API does return (GET /studies).
 */
export const DISEASE_DESCRIPTIONS: Record<DiseaseCode, string> = {
  ASMA: "Casos de asma associados a umidade relativa e ponto de orvalho, com defasagem climática de 1 mês.",
  "BRONQUITE AGUDA":
    "Casos de bronquite aguda associados a umidade e precipitação, com defasagem de até 3 meses.",
  "BRONQUITE CRÔNICA":
    "Casos de bronquite crônica associados à intensidade de rajadas de vento.",
  "INFARTO AGUDO DO MIOCÁRDIO":
    "Casos de infarto associados à velocidade média do vento do mês anterior.",
  "INSUFICIÊNCIA CARDÍACA":
    "Casos de insuficiência cardíaca associados a pressão atmosférica e ponto de orvalho.",
  LEPTOSPIROSE:
    "Casos de leptospirose associados a precipitação e umidade relativa do mês anterior -- o padrão sazonal mais forte da base.",
};

/**
 * Climate fields on EpidemiologicalRecord (types/data.ts), paired with
 * a display label -- backs the variable picker in the per-study
 * dashboard (components/studies/StudyDashboardModal.tsx).
 */
export const CLIMATE_VARIABLES: {
  key: keyof EpidemiologicalRecord;
  label: string;
}[] = [
  { key: "precipitationSumMm", label: "Precipitação (mm)" },
  { key: "precipitationMaxObservationMm", label: "Precipitação máxima (mm)" },
  { key: "temperatureAvgC", label: "Temperatura média (°C)" },
  { key: "dewPointAvgC", label: "Ponto de orvalho (°C)" },
  { key: "relativeHumidityAvgPct", label: "Umidade relativa (%)" },
  { key: "atmosphericPressureAvgMb", label: "Pressão atmosférica (mb)" },
  { key: "windSpeedAvgMs", label: "Vento médio (m/s)" },
  { key: "windGustMaxMs", label: "Rajada máxima (m/s)" },
];
