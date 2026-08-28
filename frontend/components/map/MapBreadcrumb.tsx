import { ArrowLeft } from "lucide-react";

interface MapBreadcrumbProps {
  path: string[];
  onBack?: () => void;
}

export function MapBreadcrumb({ path, onBack }: MapBreadcrumbProps) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <p className="text-xs font-medium text-muted">
        {path.map((segment, i) => (
          <span key={segment}>
            {i > 0 && <span className="mx-1.5 text-muted-light">/</span>}
            <span className={i === path.length - 1 ? "text-foreground" : undefined}>
              {segment}
            </span>
          </span>
        ))}
      </p>

      {onBack && (
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-primary-600 hover:bg-primary-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Voltar para Brasil
        </button>
      )}
    </div>
  );
}
