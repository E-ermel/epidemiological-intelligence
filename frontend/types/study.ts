import type { DiseaseCode } from "@/types/epidemiology";

export interface StudySummary {
  disease: DiseaseCode;
  label: string;
  description: string;
  totalCases: number;
  municipalityCount: number;
  /** null when the disease has epidemiological data but no trained model yet. */
  activeModelVersion: string | null;
}
