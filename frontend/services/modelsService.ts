import type { DiseaseCode } from "@/types/epidemiology";
import type { ModelMetadata, ObservedVsPredictedPoint } from "@/types/model";
import { MOCK_MODELS, getMockModel, getMockObservedVsPredicted } from "@/mocks/models";

/**
 * TODO: backend endpoint required. model_tools.py already reads
 * metadata.json/metrics.json/predictions.parquet from GCS via
 * latest.json, but only as an agent tool. Once a plain HTTP endpoint
 * exists (e.g. GET /models, GET /models/{disease}/predictions), swap
 * the bodies below for services/api.ts calls -- signatures stay the same.
 */

export async function getModels(): Promise<ModelMetadata[]> {
  return MOCK_MODELS;
}

export async function getModel(disease: DiseaseCode): Promise<ModelMetadata | undefined> {
  return getMockModel(disease);
}

export async function getObservedVsPredicted(
  disease: DiseaseCode
): Promise<ObservedVsPredictedPoint[]> {
  return getMockObservedVsPredicted(disease);
}
