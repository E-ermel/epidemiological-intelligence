import type { MunicipalityOption } from "@/types/data";
import { getMunicipalitiesData } from "@/services/api";

/** Municipalities of one state (UF code), for the municipality picker. */
export async function getMunicipalities(state: string): Promise<MunicipalityOption[]> {
  return getMunicipalitiesData(state);
}
