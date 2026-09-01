import type { DiseaseCode } from "@/types/epidemiology";
import type { ModelMetadata, ObservedVsPredictedPoint } from "@/types/model";
import {
  type ApiRetrainExecutionStatus,
  getModelPredictions,
  getModelsData,
  getRetrainExecutionStatus,
  retrainAllModels as retrainAllModelsApi,
  retrainModel,
} from "@/services/api";

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

export async function retrainDiseaseModel(disease: DiseaseCode): Promise<string> {
  const { executionName } = await retrainModel(disease);
  return executionName;
}

export async function retrainAllModels(): Promise<string> {
  const { executionName } = await retrainAllModelsApi();
  return executionName;
}

export async function getRetrainStatus(
  executionName: string
): Promise<ApiRetrainExecutionStatus> {
  return getRetrainExecutionStatus(executionName);
}
