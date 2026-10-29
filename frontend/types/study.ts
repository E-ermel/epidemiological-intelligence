import type { DiseaseCode } from "@/types/epidemiology";

export interface StudySummary {
  disease: DiseaseCode;
  label: string;
  description: string;
  totalCases: number;
  municipalityCount: number;
  /**
   * Outbreak alert ("fechado" origin): states in alert in any of the next
   * 3 months and the highest outbreak probability among them. null when
   * the alert job hasn't run yet or the disease isn't alerted (Oropouche).
   */
  statesInAlert: number | null;
  maxAlertProbability: number | null;
}
