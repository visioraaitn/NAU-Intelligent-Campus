import type { ConversationDetail, ConversationPage, ConversationSummary } from "../types/conversation";
import { apiRequest } from "./http";

export const conversationApi = {
  list(limit = 30, offset = 0): Promise<ConversationPage> {
    return apiRequest(`/conversations?limit=${limit}&offset=${offset}`);
  },
  create(titleSource: string): Promise<ConversationSummary> {
    return apiRequest("/conversations", { method: "POST", body: { title_source: titleSource } });
  },
  get(id: string): Promise<ConversationDetail> {
    return apiRequest(`/conversations/${encodeURIComponent(id)}`);
  },
  rename(id: string, title: string): Promise<ConversationSummary> {
    return apiRequest(`/conversations/${encodeURIComponent(id)}`, { method: "PATCH", body: { title } });
  },
  delete(id: string): Promise<void> {
    return apiRequest(`/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
  },
};
