import type { EpidemiologicalDataFilters, EpidemiologicalRecord } from "@/types/data";
import { getEpidemiologicalData } from "@/services/api";

export async function queryEpidemiologicalData(
  filters: EpidemiologicalDataFilters
): Promise<EpidemiologicalRecord[]> {
  return getEpidemiologicalData(filters);
}
