import type { StudySummary } from "@/types/study";
import { MOCK_DISEASE_DISTRIBUTION } from "@/mocks/overview";
import { getMockModel } from "@/mocks/models";

/**
 * MOCK DATA. "Estudo" here means: one disease, its epidemiological
 * series in the Gold table, and its trained model -- there is no
 * dedicated backend concept or endpoint for this grouping yet.
 * TODO: backend endpoint required (e.g. GET /studies).
 */

const DESCRIPTIONS: Record<string, string> = {
  ASMA:
    "Casos de asma associados a umidade relativa e ponto de orvalho, com defasagem climática de 1 mês.",
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

export const MOCK_STUDIES: StudySummary[] = MOCK_DISEASE_DISTRIBUTION.map((slice) => ({
  disease: slice.disease,
  label: slice.label,
  description: DESCRIPTIONS[slice.disease] ?? "",
  totalCases: slice.cases,
  municipalityCount: 148,
  activeModelVersion: getMockModel(slice.disease)?.model_version ?? "—",
}));
