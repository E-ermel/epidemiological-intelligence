import type { DiseaseCode } from "@/types/epidemiology";

/**
 * Mirrors the metadata.json produced by build_model_metadata()
 * (data_science/src/epidemiological_intelligence/artifacts/metadata.py)
 * and pointed to by <disease>/latest.json in GCS. Kept field-for-field
 * identical so the mock can be swapped for a real API response later
 * without touching any component.
 */
export interface ModelMetrics {
  mae: number;
  rmse: number;
  r2: number;
  wape_pct: number;
}

export interface ModelComparison {
  base: ModelMetrics;
  final: ModelMetrics;
  mae_improvement_pct: number;
  rmse_improvement_pct: number;
}

export interface ModelMetadata {
  disease: DiseaseCode;
  model_version: string;
  run_id: string;
  trained_at: string;
  model_type: string;
  features: string[];
  training_period: { start: string; end: string };
  test_period: { start: string; end: string };
  metrics: ModelComparison;
}

export interface ObservedVsPredictedPoint {
  referenceDate: string;
  municipality: string;
  observedCases: number;
  predictedCases: number;
}
