import { AlertCircle, Bot, User } from "lucide-react";
import type { ChatMessage } from "@/types/chat";
import { cn } from "@/lib/utils";

export function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <span
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-foreground text-white" : "bg-primary-600 text-white"
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </span>

      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-foreground text-white"
            : message.status === "error"
              ? "bg-danger-light text-danger"
              : "bg-surface-muted text-foreground"
        )}
      >
        {message.status === "error" && (
          <div className="mb-1 flex items-center gap-1 text-xs font-medium">
            <AlertCircle className="h-3.5 w-3.5" />
            Erro ao consultar o agente
          </div>
        )}
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
