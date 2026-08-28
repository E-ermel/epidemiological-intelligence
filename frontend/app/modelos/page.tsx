import { Suspense } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingState } from "@/components/ui/LoadingState";
import { ModelsExplorer } from "@/components/models/ModelsExplorer";
import { getModels, getObservedVsPredicted } from "@/services/modelsService";

export const dynamic = "force-dynamic";

export default async function ModelsPage() {
  const models = await getModels();

  const observedVsPredictedEntries = await Promise.all(
    models.map(async (model) => [model.disease, await getObservedVsPredicted(model.disease)] as const)
  );
  const observedVsPredictedByDisease = Object.fromEntries(observedVsPredictedEntries);

  return (
    <div>
      <PageHeader
        title="Modelos"
        description="Versão ativa, features climáticas e desempenho de cada modelo preditivo."
      />

      <Suspense fallback={<LoadingState />}>
        <ModelsExplorer
          models={models}
          observedVsPredictedByDisease={observedVsPredictedByDisease}
        />
      </Suspense>
    </div>
  );
}
