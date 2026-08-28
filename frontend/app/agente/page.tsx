import { PageHeader } from "@/components/ui/PageHeader";
import { ChatPanel } from "@/components/agent/ChatPanel";

export default function AgentPage() {
  return (
    <div>
      <PageHeader
        title="Assistente Epidemiológico"
        description="Converse com o agente sobre casos, métricas de modelos, previsões e metodologia."
      />
      <ChatPanel />
    </div>
  );
}
