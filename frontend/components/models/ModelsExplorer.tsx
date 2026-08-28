"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { DiseaseCode } from "@/types/epidemiology";
import type { ModelMetadata, ObservedVsPredictedPoint } from "@/types/model";
import { ModelCard } from "@/components/models/ModelCard";
import { ModelDetail } from "@/components/models/ModelDetail";
import { DISEASES } from "@/lib/constants";

interface ModelsExplorerProps {
  models: ModelMetadata[];
  observedVsPredictedByDisease: Record<string, ObservedVsPredictedPoint[]>;
}

export function ModelsExplorer({ models, observedVsPredictedByDisease }: ModelsExplorerProps) {
  const searchParams = useSearchParams();
  const requestedDisease = searchParams.get("disease") as DiseaseCode | null;

  const [selected, setSelected] = useState<DiseaseCode>(
    requestedDisease && models.some((m) => m.disease === requestedDisease)
      ? requestedDisease
      : models[0]?.disease
  );

  const labelByDisease = useMemo(
    () => Object.fromEntries(DISEASES.map((d) => [d.code, d.label])),
    []
  );

  const selectedModel = models.find((model) => model.disease === selected);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="flex flex-col gap-3">
        {models.map((model) => (
          <ModelCard
            key={model.disease}
            model={model}
            label={labelByDisease[model.disease] ?? model.disease}
            isSelected={model.disease === selected}
            onSelect={() => setSelected(model.disease)}
          />
        ))}
      </div>

      <div className="lg:col-span-2">
        {selectedModel && (
          <ModelDetail
            label={labelByDisease[selectedModel.disease] ?? selectedModel.disease}
            model={selectedModel}
            observedVsPredicted={observedVsPredictedByDisease[selectedModel.disease] ?? []}
          />
        )}
      </div>
    </div>
  );
}
