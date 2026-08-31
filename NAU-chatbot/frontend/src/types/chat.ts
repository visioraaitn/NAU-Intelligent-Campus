export interface ChatSessionResponse {
  session_id: string;
  expires_in: number;
}

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  requestId?: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  delivery: "sent" | "failed";
}
