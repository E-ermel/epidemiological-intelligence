import { AlertTriangle } from "lucide-react";

export function ErrorState({
  title = "Não foi possível carregar os dados",
  description,
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl bg-danger-light py-10 text-center">
      <AlertTriangle className="h-5 w-5 text-danger" />
      <span className="text-sm font-medium text-danger">{title}</span>
      {description && <span className="max-w-sm text-xs text-danger/80">{description}</span>}
    </div>
  );
}
