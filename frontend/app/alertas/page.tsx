import { BellOff } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { AlertModelCard } from "@/components/alerts/AlertModelCard";
import { AlertsExplorer } from "@/components/alerts/AlertsExplorer";
import { ApiError, getAlertModel, getAlerts, getAlertStates } from "@/services/api";

export const dynamic = "force-dynamic";

async function loadAlerts() {
  try {
    const [model, states, rows] = await Promise.all([
      getAlertModel(),
      getAlertStates("fechado", 1),
      getAlerts({ level: "uf", originType: "fechado", horizon: 1, onlyAlerts: true, limit: 300 }),
    ]);
    return { status: "ok" as const, model, states, rows };
  } catch (error) {
    // 404 em /alerts/model: o job do alerta ainda não rodou nenhuma vez.
    if (error instanceof ApiError && error.status === 404) return { status: "empty" as const };
    return { status: "error" as const };
  }
}

export default async function AlertsPage() {
  const result = await loadAlerts();

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Alertas de surto"
        description="Probabilidade de surto de cada doença nos próximos 1 a 3 meses, por UF e por município. Atualizado todo mês."
      />

      {result.status === "empty" ? (
        <EmptyState
          icon={BellOff}
          title="O alerta ainda não foi gerado"
          description="Ele é calculado pelo pipeline mensal logo depois que os dados são atualizados."
        />
      ) : result.status === "error" ? (
        <ErrorState description="Tente novamente em alguns instantes." />
      ) : (
        <>
          <AlertsExplorer model={result.model} initialStates={result.states} initialRows={result.rows} />
          <AlertModelCard info={result.model} />
        </>
      )}
    </div>
  );
}
