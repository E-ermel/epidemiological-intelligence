import { Loader2 } from "lucide-react";

export function LoadingState({ label = "Carregando..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-muted">
      <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
