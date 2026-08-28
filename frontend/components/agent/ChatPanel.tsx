"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import type { ChatMessage } from "@/types/chat";
import { SUGGESTED_QUESTIONS } from "@/types/chat";
import { ChatMessageBubble } from "@/components/agent/ChatMessageBubble";
import { ChatInput } from "@/components/agent/ChatInput";
import { Card } from "@/components/ui/Card";
import { ApiError, sendChatMessage } from "@/services/api";

function createId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const conversationId = useRef(createId());
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSend(content: string) {
    const userMessage: ChatMessage = { id: createId(), role: "user", content };
    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);

    try {
      const response = await sendChatMessage({
        message: content,
        conversation_id: conversationId.current,
      });

      setMessages((prev) => [
        ...prev,
        { id: createId(), role: "assistant", content: response.answer },
      ]);
    } catch (error) {
      const description =
        error instanceof ApiError ? error.message : "Erro inesperado ao consultar o agente.";

      setMessages((prev) => [
        ...prev,
        { id: createId(), role: "assistant", content: description, status: "error" },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  return (
    <Card className="flex h-[calc(100vh-220px)] min-h-[420px] flex-col p-0">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-5">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-50 text-primary-600">
              <Sparkles className="h-6 w-6" />
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">
                Pergunte sobre casos, modelos ou metodologia
              </p>
              <p className="mt-1 text-xs text-muted">
                O assistente consulta o BigQuery, os artefatos dos modelos e a documentação de
                metodologia do projeto.
              </p>
            </div>

            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTED_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => handleSend(question)}
                  className="rounded-full border border-border px-3 py-1.5 text-xs text-muted hover:border-primary-500 hover:text-primary-700"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {messages.map((message) => (
              <ChatMessageBubble key={message.id} message={message} />
            ))}
            {isSending && (
              <ChatMessageBubble
                message={{ id: "pending", role: "assistant", content: "Consultando..." }}
              />
            )}
          </div>
        )}
      </div>

      <div className="border-t border-border p-4">
        <ChatInput onSubmit={handleSend} disabled={isSending} />
      </div>
    </Card>
  );
}
