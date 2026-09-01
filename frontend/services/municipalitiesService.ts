import { getMunicipalitiesData } from "@/services/api";

export async function getMunicipalities(): Promise<string[]> {
  return getMunicipalitiesData();
}
