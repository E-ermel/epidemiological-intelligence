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
 * Every disease in the Gold table (see types/epidemiology.ts). The
 * first group comes from SIH/SUS hospitalizations, the second from
 * SINAN notifications.
 */
export const DISEASES: { code: DiseaseCode; label: string }[] = [
  { code: "ASMA", label: "Asma" },
  { code: "BRONQUITE AGUDA", label: "Bronquite Aguda" },
  { code: "BRONQUITE CRÔNICA", label: "Bronquite Crônica" },
  { code: "INFARTO AGUDO DO MIOCÁRDIO", label: "Infarto Agudo do Miocárdio" },
  { code: "INSUFICIÊNCIA CARDÍACA", label: "Insuficiência Cardíaca" },
  { code: "OROPOUCHE", label: "Oropouche" },
  { code: "LEPTOSPIROSE", label: "Leptospirose" },
  { code: "ACIDENTE POR ESCORPIÃO", label: "Acidente por Escorpião" },
  { code: "ACIDENTE POR SERPENTE", label: "Acidente por Serpente" },
  { code: "ACIDENTE POR ARANHA", label: "Acidente por Aranha" },
  { code: "ACIDENTE POR ABELHA", label: "Acidente por Abelha" },
  { code: "ACIDENTE POR LAGARTA", label: "Acidente por Lagarta" },
  { code: "ACIDENTE POR OUTRO ANIMAL PEÇONHENTO", label: "Outros Animais Peçonhentos" },
];

export const DISEASE_LABELS: Record<DiseaseCode, string> = Object.fromEntries(
  DISEASES.map((d) => [d.code, d.label])
) as Record<DiseaseCode, string>;

/**
 * One color per disease, reused everywhere a disease needs a visual
 * identity (DiseaseDistributionChart) so the same disease reads as the
 * same color across the app. The 6 hospitalization diseases keep the
 * original cool hues; the SINAN diseases get muted warm/green hues.
 * With 13 slices some pairs are close, so the list under the chart
 * repeats each color next to its name and percentage.
 */
export const DISEASE_COLORS: Record<DiseaseCode, string> = {
  ASMA: "#2563eb",
  "BRONQUITE AGUDA": "#0891b2",
  "BRONQUITE CRÔNICA": "#4f46e5",
  "INFARTO AGUDO DO MIOCÁRDIO": "#0d9488",
  "INSUFICIÊNCIA CARDÍACA": "#7c3aed",
  OROPOUCHE: "#64748b",
  LEPTOSPIROSE: "#0369a1",
  "ACIDENTE POR ESCORPIÃO": "#d97706",
  "ACIDENTE POR SERPENTE": "#15803d",
  "ACIDENTE POR ARANHA": "#be123c",
  "ACIDENTE POR ABELHA": "#ca8a04",
  "ACIDENTE POR LAGARTA": "#65a30d",
  "ACIDENTE POR OUTRO ANIMAL PEÇONHENTO": "#9a3412",
};

/** UF codes and names, for the state pickers. */
export const STATES: { code: string; name: string }[] = [
  { code: "AC", name: "Acre" },
  { code: "AL", name: "Alagoas" },
  { code: "AM", name: "Amazonas" },
  { code: "AP", name: "Amapá" },
  { code: "BA", name: "Bahia" },
  { code: "CE", name: "Ceará" },
  { code: "DF", name: "Distrito Federal" },
  { code: "ES", name: "Espírito Santo" },
  { code: "GO", name: "Goiás" },
  { code: "MA", name: "Maranhão" },
  { code: "MG", name: "Minas Gerais" },
  { code: "MS", name: "Mato Grosso do Sul" },
  { code: "MT", name: "Mato Grosso" },
  { code: "PA", name: "Pará" },
  { code: "PB", name: "Paraíba" },
  { code: "PE", name: "Pernambuco" },
  { code: "PI", name: "Piauí" },
  { code: "PR", name: "Paraná" },
  { code: "RJ", name: "Rio de Janeiro" },
  { code: "RN", name: "Rio Grande do Norte" },
  { code: "RO", name: "Rondônia" },
  { code: "RR", name: "Roraima" },
  { code: "RS", name: "Rio Grande do Sul" },
  { code: "SC", name: "Santa Catarina" },
  { code: "SE", name: "Sergipe" },
  { code: "SP", name: "São Paulo" },
  { code: "TO", name: "Tocantins" },
];

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
  OROPOUCHE:
    "Internações por febre do Oropouche (CID A93.0). Quase só zeros antes de 2024, quando a doença se espalhou para fora da Amazônia.",
  LEPTOSPIROSE:
    "Casos de leptospirose associados a precipitação e umidade relativa do mês anterior -- o padrão sazonal mais forte da base.",
  "ACIDENTE POR ESCORPIÃO":
    "Notificações de acidentes com escorpião -- o tipo mais comum no país, urbano e fortemente sazonal.",
  "ACIDENTE POR SERPENTE":
    "Notificações de acidentes ofídicos, concentrados em áreas rurais e na estação chuvosa.",
  "ACIDENTE POR ARANHA": "Notificações de acidentes com aranha (araneísmo).",
  "ACIDENTE POR ABELHA": "Notificações de acidentes com abelha.",
  "ACIDENTE POR LAGARTA": "Notificações de acidentes com lagarta (erucismo).",
  "ACIDENTE POR OUTRO ANIMAL PEÇONHENTO":
    "Notificações de acidentes com outros animais peçonhentos ou com o animal não identificado.",
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
