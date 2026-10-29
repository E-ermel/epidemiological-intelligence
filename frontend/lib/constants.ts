import type { DiseaseCode } from "@/types/epidemiology";
import type { EpidemiologicalRecord } from "@/types/data";

export const APP_NAME = "Epidemiological Intelligence";
export const APP_SUBTITLE = "Plataforma de Inteligência Epidemiológica";

export const NAV_ITEMS = [
  { label: "Visão Geral", href: "/" },
  { label: "Estudos", href: "/estudos" },
  { label: "Explorar Dados", href: "/dados" },
  { label: "Alertas", href: "/alertas" },
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
  ASMA: "Internações por asma. Sobem no frio: a 13 °C, o risco é cerca de 19% maior que na temperatura mediana.",
  "BRONQUITE AGUDA":
    "Internações por bronquite aguda, fortemente sazonais. O frio aumenta o risco em cerca de 40%.",
  "BRONQUITE CRÔNICA":
    "Internações por bronquite crônica/DPOC. É a doença mais sensível ao frio: risco cerca de 55% maior a 13 °C.",
  "INFARTO AGUDO DO MIOCÁRDIO":
    "Internações por infarto. Sobem nos extremos de temperatura: +10% no frio e +17% no calor (31 °C).",
  "INSUFICIÊNCIA CARDÍACA":
    "Internações por insuficiência cardíaca, cerca de 19% mais frequentes nos meses frios.",
  OROPOUCHE:
    "Internações por febre do Oropouche (CID A93.0). Quase só zeros antes de 2024, quando a doença se espalhou para fora da Amazônia; ainda sem alerta.",
  LEPTOSPIROSE:
    "Casos confirmados de leptospirose. É a doença mais ligada à chuva: um mês muito chuvoso multiplica o risco por até 3,7, com efeito no próprio mês e no seguinte.",
  "ACIDENTE POR ESCORPIÃO":
    "Notificações de acidentes com escorpião -- o tipo mais comum no país, urbano e fortemente sazonal (raros no frio).",
  "ACIDENTE POR SERPENTE":
    "Notificações de acidentes ofídicos, concentrados em áreas rurais e nos meses quentes.",
  "ACIDENTE POR ARANHA":
    "Notificações de acidentes com aranha, que no Sul têm pico no outono e no inverno.",
  "ACIDENTE POR ABELHA": "Notificações de acidentes com abelha, mais comuns nos meses quentes e secos.",
  "ACIDENTE POR LAGARTA":
    "Notificações de acidentes com lagarta (erucismo), que sobem com a chuva (risco até 3,1 vezes maior).",
  "ACIDENTE POR OUTRO ANIMAL PEÇONHENTO":
    "Notificações de acidentes com outros animais peçonhentos ou com o animal não identificado.",
};

/** Diseases from SIH/SUS hospitalizations; the rest come from SINAN notifications. */
export const HOSPITALIZATION_DISEASES: DiseaseCode[] = DISEASES.slice(0, 6).map((d) => d.code);

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
