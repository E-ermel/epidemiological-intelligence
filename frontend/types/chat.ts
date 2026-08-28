/**
 * Mirrors ai/src/epidemiological_agent/api/schemas.py exactly --
 * this is the one real, existing backend contract in this app.
 */
export interface ChatRequest {
  message: string;
  conversation_id: string;
}

export interface ChatResponse {
  answer: string;
  conversation_id: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "pending" | "error";
}

/** Suggested prompts shown on the Agente IA page -- illustrative only. */
export const SUGGESTED_QUESTIONS = [
  "Quantos casos de leptospirose ocorreram em Porto Alegre em 2024?",
  "Quais as métricas do modelo de asma?",
  "Qual a previsão de bronquite aguda para os próximos meses?",
  "Como o modelo de infarto foi construído?",
] as const;
