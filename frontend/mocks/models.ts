import type { DiseaseCode } from "@/types/epidemiology";
import type { ModelMetadata, ObservedVsPredictedPoint } from "@/types/model";

/**
 * MOCK DATA, shaped field-for-field like the real metadata.json written
 * by build_model_metadata()
 * (data_science/src/epidemiological_intelligence/artifacts/metadata.py)
 * and referenced by <disease>/latest.json in GCS. The AI service reads
 * this from GCS via model_tools.py, but only as an agent tool -- there
 * is no HTTP endpoint yet.
 * TODO: backend endpoint required (e.g. GET /models or GET /models/{disease}).
 */

interface ModelSeed {
  disease: DiseaseCode;
  features: string[];
  mae: number;
  rmse: number;
  r2: number;
  wapePct: number;
  improvementPct: number;
}

const MODEL_SEEDS: ModelSeed[] = [
  {
    disease: "ASMA",
    features: ["relative_humidity_avg_pct", "dew_point_avg_c_lag1"],
    mae: 3.8,
    rmse: 5.1,
    r2: 0.71,
    wapePct: 14.2,
    improvementPct: 22.5,
  },
  {
    disease: "BRONQUITE AGUDA",
    features: ["relative_humidity_avg_pct", "precipitation_avg_observation_mm_lag3"],
    mae: 4.2,
    rmse: 5.9,
    r2: 0.66,
    wapePct: 16.8,
    improvementPct: 18.1,
  },
  {
    disease: "BRONQUITE CRÔNICA",
    features: ["wind_gust_max_ms"],
    mae: 2.1,
    rmse: 3.0,
    r2: 0.58,
    wapePct: 19.4,
    improvementPct: 12.7,
  },
  {
    disease: "INFARTO AGUDO DO MIOCÁRDIO",
    features: ["wind_speed_avg_ms_lag1"],
    mae: 1.9,
    rmse: 2.6,
    r2: 0.54,
    wapePct: 21.0,
    improvementPct: 9.8,
  },
  {
    disease: "INSUFICIÊNCIA CARDÍACA",
    features: ["atmospheric_pressure_avg_mb", "dew_point_avg_c"],
    mae: 2.6,
    rmse: 3.5,
    r2: 0.61,
    wapePct: 17.6,
    improvementPct: 15.3,
  },
  {
    disease: "LEPTOSPIROSE",
    features: ["precipitation_sum_mm_lag1", "relative_humidity_avg_pct_lag1"],
    mae: 5.4,
    rmse: 7.3,
    r2: 0.69,
    wapePct: 13.5,
    improvementPct: 26.4,
  },
];

function baseMetricsFor(seed: ModelSeed) {
  // Base model (municipality + month only) is deliberately worse than
  // final -- mirrors what train.py actually compares.
  return {
    mae: Number((seed.mae * 1.35).toFixed(2)),
    rmse: Number((seed.rmse * 1.3).toFixed(2)),
    r2: Number((seed.r2 * 0.7).toFixed(2)),
    wape_pct: Number((seed.wapePct * 1.3).toFixed(1)),
  };
}

export const MOCK_MODELS: ModelMetadata[] = MODEL_SEEDS.map((seed, i) => ({
  disease: seed.disease,
  model_version: "v3",
  run_id: `2024071${i}T090000Z`,
  trained_at: `2024-07-1${i}T09:00:00+00:00`,
  model_type: "Negative Binomial",
  features: seed.features,
  training_period: { start: "2019-01-01", end: "2023-12-01" },
  test_period: { start: "2024-01-01", end: "2024-06-01" },
  metrics: {
    base: baseMetricsFor(seed),
    final: {
      mae: seed.mae,
      rmse: seed.rmse,
      r2: seed.r2,
      wape_pct: seed.wapePct,
    },
    mae_improvement_pct: seed.improvementPct,
    rmse_improvement_pct: Number((seed.improvementPct * 0.85).toFixed(1)),
  },
}));

export function getMockModel(disease: DiseaseCode): ModelMetadata | undefined {
  return MOCK_MODELS.find((model) => model.disease === disease);
}

export function getMockObservedVsPredicted(
  disease: DiseaseCode
): ObservedVsPredictedPoint[] {
  const seed = MODEL_SEEDS.find((s) => s.disease === disease);
  const noise = seed ? seed.mae : 3;

  return Array.from({ length: 6 }, (_, i) => {
    const date = new Date("2024-01-01");
    date.setMonth(date.getMonth() + i);
    const observed = Math.round(18 + Math.sin(i / 2) * 6 + i * 0.8);
    const predicted = Math.round(observed + (i % 2 === 0 ? noise * 0.4 : -noise * 0.3));

    return {
      referenceDate: date.toISOString().slice(0, 10),
      municipality: "Porto Alegre",
      observedCases: observed,
      predictedCases: predicted,
    };
  });
}
