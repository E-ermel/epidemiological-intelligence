import type { ModelMetadata } from "@/types/model";
import { Badge } from "@/components/ui/Badge";
import { cn, formatDate } from "@/lib/utils";

interface ModelCardProps {
  model?: ModelMetadata;
  label: string;
  isSelected?: boolean;
  onSelect?: () => void;
}

export function ModelCard({ model, label, isSelected, onSelect }: ModelCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-2xl border p-4 text-left transition-colors",
        isSelected
          ? "border-primary-500 bg-primary-50"
          : "border-border bg-surface hover:border-border-strong"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-foreground">{label}</span>
        {model ? (
          <Badge tone={isSelected ? "primary" : "neutral"}>{model.model_version}</Badge>
        ) : (
          <Badge tone="neutral">sem modelo</Badge>
        )}
      </div>

      {model ? (
        <>
          <p className="mt-1 text-xs text-muted">{model.model_type}</p>

          <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div>
              <dt className="text-muted-light">MAE</dt>
              <dd className="font-medium text-foreground">{model.metrics.final.mae.toFixed(2)}</dd>
            </div>
            <div>
              <dt className="text-muted-light">R²</dt>
              <dd className="font-medium text-foreground">{model.metrics.final.r2.toFixed(2)}</dd>
            </div>
          </dl>

          <p className="mt-3 text-[11px] text-muted-light">
            Treinado em {formatDate(model.trained_at)}
          </p>
        </>
      ) : (
        <p className="mt-1 text-xs text-muted">Nenhum modelo treinado ainda.</p>
      )}
    </button>
  );
}
