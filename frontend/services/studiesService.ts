import type { DiseaseCode } from "@/types/epidemiology";
import type { StudySummary } from "@/types/study";
import { getStudiesData } from "@/services/api";
import { DISEASE_DESCRIPTIONS, DISEASE_LABELS } from "@/lib/constants";

export async function getStudies(): Promise<StudySummary[]> {
  const studies = await getStudiesData();

  return studies.map((study) => {
    const disease = study.disease as DiseaseCode;

    return {
      disease,
      label: DISEASE_LABELS[disease] ?? study.disease,
      description: DISEASE_DESCRIPTIONS[disease] ?? "",
      totalCases: study.totalCases,
      municipalityCount: study.municipalityCount,
      activeModelVersion: study.activeModelVersion,
    };
  });
}
