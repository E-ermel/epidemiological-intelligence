import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { RetrainButton, type RetrainStatus } from "@/components/models/RetrainButton";
import { FlaskConical } from "lucide-react";

export function UntrainedModelPanel({
  label,
  retrainStatus,
  onRetrain,
}: {
  label: string;
  retrainStatus: RetrainStatus;
  onRetrain: () => void;
}) {
  return (
    <Card className="flex flex-col items-center gap-4">
      <EmptyState
        icon={FlaskConical}
        title={`Nenhum modelo treinado para ${label}`}
        description="Os dados epidemiológicos dessa doença já estão disponíveis -- falta treinar o modelo preditivo."
      />
      <RetrainButton status={retrainStatus} onRetrain={onRetrain} align="center" />
    </Card>
  );
}
