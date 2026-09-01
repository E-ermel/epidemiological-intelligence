import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

export type RetrainStatus =
  | "idle"
  | "loading"
  | "running"
  | "succeeded"
  | "failed"
  | "error";

const STATUS_MESSAGE: Partial<Record<RetrainStatus, string>> = {
  loading: "Solicitando o treino...",
  running: "Treino em andamento -- isso pode levar até uma hora.",
  succeeded: "Treino concluído com sucesso.",
  failed: "O treino falhou. Confira os logs para mais detalhes.",
  error: "Não foi possível iniciar o retreino. Tente novamente.",
};

// Real signal we actually have (see GET /models/retrain/status): the job
// was accepted, is running, or reached a terminal state. There's no
// finer-grained per-disease progress to report, so the tracker has
// exactly these 3 stops -- not a fabricated percentage.
const STEPS = ["Solicitado", "Treinando", "Concluído"] as const;

function stepIndexForStatus(status: RetrainStatus): number {
  if (status === "loading") return 0;
  if (status === "running") return 1;
  if (status === "succeeded" || status === "failed") return 2;
  return -1;
}

function RetrainProgressSteps({ status }: { status: RetrainStatus }) {
  const activeIndex = stepIndexForStatus(status);
  if (activeIndex === -1) return null;

  const isFailed = status === "failed";

  return (
    <div className="flex items-center" aria-label={`Progresso do treino: ${STEPS[activeIndex]}`}>
      {STEPS.map((stepLabel, index) => {
        const isFinalFailed = index === 2 && isFailed;
        const isDone = index < activeIndex;
        const isCurrentTerminal = index === activeIndex && index === 2;
        const isCurrentPending = index === activeIndex && index < 2;

        return (
          <div key={stepLabel} className="flex items-center">
            <span
              title={stepLabel}
              className={cn(
                "h-2 w-2 rounded-full transition-colors",
                isFinalFailed
                  ? "bg-danger"
                  : isDone || isCurrentTerminal
                    ? "bg-primary-500"
                    : isCurrentPending
                      ? "bg-primary-500 animate-pulse"
                      : "bg-border-strong"
              )}
            />
            {index < STEPS.length - 1 && (
              <span
                className={cn(
                  "h-px w-4",
                  index < activeIndex ? "bg-primary-500" : "bg-border-strong"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/**
 * The button stays disabled for the whole "loading" -> "running" span,
 * not just while the trigger request is in flight -- a real result
 * (succeeded/failed) is what re-enables it, not just job acceptance.
 */
export function RetrainButton({
  status,
  onRetrain,
  label = "Retreinar modelo",
  align = "end",
}: {
  status: RetrainStatus;
  onRetrain: () => void;
  label?: string;
  /** "end" fits a card header (button in the top-right corner); "center"
   * fits a centered empty-state panel -- otherwise the progress steps and
   * message end up right-aligned against a button that's itself centered
   * by its parent, reading as misaligned. */
  align?: "end" | "center";
}) {
  const message = STATUS_MESSAGE[status] ?? null;
  const isBusy = status === "loading" || status === "running";
  const isError = status === "failed" || status === "error";

  return (
    <div className={cn("flex flex-col gap-1.5", align === "end" ? "items-end" : "items-center")}>
      <button
        type="button"
        onClick={onRetrain}
        disabled={isBusy}
        className="flex items-center gap-1.5 rounded-full border border-border-strong px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:border-primary-500 hover:text-primary-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <RefreshCw className={cn("h-3.5 w-3.5", isBusy && "animate-spin")} />
        {label}
      </button>
      <RetrainProgressSteps status={status} />
      {message && (
        <span
          className={cn(
            "max-w-48 text-[11px]",
            align === "end" ? "text-right" : "text-center",
            isError ? "text-danger" : "text-muted-light"
          )}
        >
          {message}
        </span>
      )}
    </div>
  );
}
