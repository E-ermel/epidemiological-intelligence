import type { StudySummary } from "@/types/study";
import { MOCK_STUDIES } from "@/mocks/studies";

/**
 * TODO: backend endpoint required (e.g. GET /studies). See mocks/studies.ts.
 */
export async function getStudies(): Promise<StudySummary[]> {
  return MOCK_STUDIES;
}
