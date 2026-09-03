import { useCallback, useEffect, useRef, useState } from "react";
import { chatApi } from "../../api/chat";
import { conversationApi } from "../../api/conversations";
import type { ChatMessage } from "../../types/chat";
import { errorMessage } from "../../utils/errors";
import { createClientId } from "../../utils/id";

type ChatStatus = "connecting" | "ready" | "sending" | "error";

interface UseChatOptions {
  conversationId?: string;
  onConversationCreated?: (id: string) => void;
  onConversationChanged?: () => void;
}

export function useChat(options: UseChatOptions = {}) {
  const { conversationId, onConversationCreated, onConversationChanged } = options;
  const [sessionId, setSessionId] = useState<string | null>(conversationId ?? null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>(conversationId ? "connecting" : "ready");
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const sessionRef = useRef<string | null>(conversationId ?? null);
  const sessionPromiseRef = useRef<Promise<string> | null>(null);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const loadConversation = useCallback(async (id: string) => {
    setStatus("connecting");
    setError(null);
    try {
      const detail = await conversationApi.get(id);
      if (!mounted.current || sessionRef.current !== id) return;
      setMessages(detail.messages.map((message) => ({
        id: message.id,
        role: message.role.toLowerCase() as "user" | "assistant",
        content: message.content,
        createdAt: message.created_at,
        delivery: "sent",
      })));
      setStatus("ready");
    } catch (reason) {
      if (!mounted.current || sessionRef.current !== id) return;
      setMessages([]);
      setError(errorMessage(reason));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    const next = conversationId ?? null;
    if (next === sessionRef.current && (next === null || messages.length > 0 || status === "sending")) return;
    sessionRef.current = next;
    setSessionId(next);
    setMessages([]);
    setError(null);
    if (next) void loadConversation(next);
    else setStatus("ready");
  }, [conversationId, loadConversation]);

  const createSession = useCallback((titleSource: string): Promise<string> => {
    if (sessionRef.current) return Promise.resolve(sessionRef.current);
    if (sessionPromiseRef.current) return sessionPromiseRef.current;
    const pending = conversationApi.create(titleSource).then((conversation) => {
      sessionRef.current = conversation.id;
      setSessionId(conversation.id);
      return conversation.id;
    }).finally(() => { sessionPromiseRef.current = null; });
    sessionPromiseRef.current = pending;
    return pending;
  }, []);

  const submit = useCallback(async (rawMessage: string, existingMessage?: ChatMessage) => {
    const content = rawMessage.trim();
    if (!content || status === "sending" || status === "connecting") return;
    const userMessage = existingMessage ?? {
      id: createClientId(),
      requestId: createClientId(),
      role: "user" as const,
      content,
      createdAt: new Date().toISOString(),
      delivery: "sent" as const,
    };
    setMessages((current) => existingMessage
      ? current.map((item) => item.id === existingMessage.id ? { ...item, delivery: "sent" } : item)
      : [...current, userMessage]);
    setStatus("sending");
    setError(null);
    try {
      const isNew = sessionRef.current === null;
      const activeSession = await createSession(content);
      const response = await chatApi.send(
        { session_id: activeSession, message: content },
        userMessage.requestId ?? userMessage.id,
      );
      const answer: ChatMessage = {
        id: createClientId(),
        role: "assistant",
        content: response.answer,
        createdAt: new Date().toISOString(),
        delivery: "sent",
      };
      if (mounted.current) {
        setMessages((current) => [...current, answer]);
        setStatus("ready");
        if (isNew) onConversationCreated?.(activeSession);
        onConversationChanged?.();
      }
    } catch (reason) {
      if (mounted.current) {
        setMessages((current) => current.map((item) => item.id === userMessage.id ? { ...item, delivery: "failed" } : item));
        setError(errorMessage(reason));
        setStatus("error");
      }
    }
  }, [createSession, onConversationChanged, onConversationCreated, status]);

  const retryLast = useCallback(() => {
    const failed = [...messages].reverse().find((item) => item.role === "user" && item.delivery === "failed");
    if (failed) void submit(failed.content, failed);
    else if (sessionRef.current) void loadConversation(sessionRef.current);
  }, [loadConversation, messages, submit]);

  const reset = useCallback(async () => {
    sessionRef.current = null;
    setSessionId(null);
    setMessages([]);
    setError(null);
    setStatus("ready");
  }, []);

  return {
    sessionId,
    messages,
    status,
    error,
    isBusy: status === "sending" || status === "connecting",
    send: (message: string) => submit(message),
    retryLast,
    reset,
    reconnect: () => sessionRef.current ? loadConversation(sessionRef.current) : Promise.resolve(),
  };
}
