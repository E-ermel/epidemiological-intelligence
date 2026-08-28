import type { DiseaseCode } from "@/types/epidemiology";

export interface StudySummary {
  disease: DiseaseCode;
  label: string;
  description: string;
  totalCases: number;
  municipalityCount: number;
  activeModelVersion: string;
}
