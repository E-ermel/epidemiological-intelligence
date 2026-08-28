import type { DiseaseCode } from "@/types/epidemiology";
import type { ModelMetadata, ObservedVsPredictedPoint } from "@/types/model";
import { getModelPredictions, getModelsData } from "@/services/api";

export async function getModels(): Promise<ModelMetadata[]> {
  return getModelsData();
}

export async function getModel(disease: DiseaseCode): Promise<ModelMetadata | undefined> {
  const models = await getModelsData();
  return models.find((model) => model.disease === disease);
}

// Predictions cover every municipality in the test period; the chart
// shows one representative series, not all of them overlaid. Porto
// Alegre (state capital, biggest series) matches the caption in
// ModelDetail.tsx.
const SAMPLE_MUNICIPALITY = "Porto Alegre";

export async function getObservedVsPredicted(
  disease: DiseaseCode
): Promise<ObservedVsPredictedPoint[]> {
  return getModelPredictions(disease, SAMPLE_MUNICIPALITY);
}
