import type { ModelMetadata, ObservedVsPredictedPoint } from "@/types/model";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ObservedVsPredictedChart } from "@/components/charts/ObservedVsPredictedChart";
import { RetrainButton, type RetrainStatus } from "@/components/models/RetrainButton";
import { formatDate } from "@/lib/utils";

interface ModelDetailProps {
  label: string;
  model: ModelMetadata;
  observedVsPredicted: ObservedVsPredictedPoint[];
  retrainStatus: RetrainStatus;
  onRetrain: () => void;
}

function MetricRow({ label, base, final }: { label: string; base: number; final: number }) {
  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-2 text-xs text-muted">{label}</td>
      <td className="py-2 text-right text-xs text-muted-light">{base.toFixed(2)}</td>
      <td className="py-2 text-right text-xs font-medium text-foreground">{final.toFixed(2)}</td>
    </tr>
  );
}

export function ModelDetail({
  label,
  model,
  observedVsPredicted,
  retrainStatus,
  onRetrain,
}: ModelDetailProps) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-foreground">{label}</h2>
            <p className="text-xs text-muted">
              {model.model_type} · versão {model.model_version} · treinado em{" "}
              {formatDate(model.trained_at)}
            </p>
          </div>
          <div className="flex items-start gap-3">
            <Badge tone="success">
              +{model.metrics.mae_improvement_pct.toFixed(1)}% MAE vs. baseline
            </Badge>
            <RetrainButton status={retrainStatus} onRetrain={onRetrain} />
          </div>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-medium text-muted-light">Período de treino</p>
            <p className="text-sm text-foreground">
              {formatDate(model.training_period.start)} – {formatDate(model.training_period.end)}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-light">Período de teste</p>
            <p className="text-sm text-foreground">
              {formatDate(model.test_period.start)} – {formatDate(model.test_period.end)}
            </p>
          </div>
        </div>

        <div className="mt-4">
          <p className="text-xs font-medium text-muted-light">Features climáticas</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {model.features.map((feature) => (
              <Badge key={feature} tone="neutral">
                {feature}
              </Badge>
            ))}
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="mb-2 text-sm font-semibold text-foreground">Métricas</h3>
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="pb-2 text-xs font-medium text-muted-light">Métrica</th>
              <th className="pb-2 text-right text-xs font-medium text-muted-light">Baseline</th>
              <th className="pb-2 text-right text-xs font-medium text-muted-light">Final</th>
            </tr>
          </thead>
          <tbody>
            <MetricRow label="MAE" base={model.metrics.base.mae} final={model.metrics.final.mae} />
            <MetricRow
              label="RMSE"
              base={model.metrics.base.rmse}
              final={model.metrics.final.rmse}
            />
            <MetricRow label="R²" base={model.metrics.base.r2} final={model.metrics.final.r2} />
            <MetricRow
              label="WAPE (%)"
              base={model.metrics.base.wape_pct}
              final={model.metrics.final.wape_pct}
            />
          </tbody>
        </table>
      </Card>

      <Card>
        <h3 className="mb-2 text-sm font-semibold text-foreground">Observado × Previsto</h3>
        <p className="mb-2 text-xs text-muted">Amostra: Porto Alegre, período de teste.</p>
        <ObservedVsPredictedChart data={observedVsPredicted} />
      </Card>
    </div>
  );
}
