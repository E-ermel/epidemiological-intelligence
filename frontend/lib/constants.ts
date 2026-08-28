import type { DiseaseCode } from "@/types/epidemiology";

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
