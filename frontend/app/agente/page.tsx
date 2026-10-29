import { PageHeader } from "@/components/ui/PageHeader";
import { ChatPanel } from "@/components/agent/ChatPanel";

export default function AgentPage() {
  return (
    <div>
      <PageHeader
        title="Assistente Epidemiológico"
        description="Converse com o agente sobre casos, clima, alertas de surto e metodologia."
      />
      <ChatPanel />
    </div>
  );
}
