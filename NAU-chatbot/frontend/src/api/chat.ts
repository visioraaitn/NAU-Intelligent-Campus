import type { ChatRequest, ChatResponse, ChatSessionResponse } from "../types/chat";
import { apiRequest } from "./http";

export const chatApi = {
  createSession(): Promise<ChatSessionResponse> {
    return apiRequest<ChatSessionResponse>("/chat/session", {
      method: "POST",
      auth: false,
    });
  },

  send(payload: ChatRequest, idempotencyKey: string): Promise<ChatResponse> {
    return apiRequest<ChatResponse>("/chat", {
      method: "POST",
      body: payload,
      headers: { "Idempotency-Key": idempotencyKey },
      auth: false,
    });
  },

  reset(sessionId: string): Promise<void> {
    return apiRequest<void>(`/chat/session/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
      auth: false,
    });
  },
};
