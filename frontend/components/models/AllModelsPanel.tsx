import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { RetrainButton, type RetrainStatus } from "@/components/models/RetrainButton";
import { LayoutGrid } from "lucide-react";

export function AllModelsPanel({
  retrainStatus,
  onRetrainAll,
}: {
  retrainStatus: RetrainStatus;
  onRetrainAll: () => void;
}) {
  return (
    <Card className="flex flex-col items-center gap-4">
      <EmptyState
        icon={LayoutGrid}
        title="Nenhuma doença selecionada"
        description="Selecione uma doença à esquerda para ver os detalhes do modelo, ou retreine todos os modelos monitorados de uma vez."
      />
      <RetrainButton
        status={retrainStatus}
        onRetrain={onRetrainAll}
        label="Retreinar modelos"
        align="center"
      />
    </Card>
  );
}
