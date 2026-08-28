import Link from "next/link";
import { Search } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { DISEASES } from "@/lib/constants";

/**
 * TODO: backend endpoint required. query_epidemiological_data
 * (ai/src/epidemiological_agent/tools/bigquery_tools.py) already
 * supports exactly these filters (disease, municipality, start_date,
 * end_date), but only as an agent tool reachable through POST /chat --
 * there is no GET /data endpoint yet. This page is a filter shell,
 * not wired to a real query, until one exists.
 */
export default function ExploreDataPage() {
  return (
    <div>
      <PageHeader
        title="Explorar Dados"
        description="Consulte os dados epidemiológicos e climáticos por doença, município e período."
      />

      <Card className="mb-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Doença
            <select
              disabled
              className="rounded-lg border border-border bg-surface-muted px-3 py-2 text-sm text-foreground disabled:cursor-not-allowed"
            >
              <option>Todas</option>
              {DISEASES.map((disease) => (
                <option key={disease.code}>{disease.label}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Município
            <input
              disabled
              placeholder="Ex.: Porto Alegre"
              className="rounded-lg border border-border bg-surface-muted px-3 py-2 text-sm text-foreground placeholder:text-muted-light disabled:cursor-not-allowed"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Data inicial
            <input
              type="date"
              disabled
              className="rounded-lg border border-border bg-surface-muted px-3 py-2 text-sm text-foreground disabled:cursor-not-allowed"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Data final
            <input
              type="date"
              disabled
              className="rounded-lg border border-border bg-surface-muted px-3 py-2 text-sm text-foreground disabled:cursor-not-allowed"
            />
          </label>
        </div>
      </Card>

      <Card>
        <EmptyState
          icon={Search}
          title="Consulta direta ainda não disponível"
          description="A FastAPI não expõe um endpoint HTTP para essa consulta ainda -- os filtros acima mostram a forma que ela terá. Por enquanto, pergunte ao Agente IA."
        />
        <div className="mt-2 flex justify-center">
          <Link
            href="/agente"
            className="rounded-lg bg-primary-600 px-4 py-2 text-xs font-medium text-white hover:bg-primary-700"
          >
            Ir para o Agente IA
          </Link>
        </div>
      </Card>
    </div>
  );
}
