import { useCallback, useEffect, useRef, useState } from "react";
import { chatApi } from "../../api/chat";
import { ApiError } from "../../api/http";
import type { ChatMessage } from "../../types/chat";
import { errorMessage } from "../../utils/errors";
import { createClientId } from "../../utils/id";

const STORAGE_KEY = "iit.chat.v2";
const MAX_STORED_MESSAGES = 60;

interface StoredChat {
  sessionId: string | null;
  messages: ChatMessage[];
}

type ChatStatus = "connecting" | "ready" | "sending" | "error";

function readStoredChat(): StoredChat {
  try {
    const parsed = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "null") as Partial<StoredChat> | null;
    if (!parsed || (parsed.sessionId !== null && typeof parsed.sessionId !== "string")) {
      return { sessionId: null, messages: [] };
    }
    const messages = Array.isArray(parsed.messages)
      ? parsed.messages.filter(
          (message): message is ChatMessage =>
            typeof message === "object" &&
            message !== null &&
            (message.role === "user" || message.role === "assistant") &&
            typeof message.content === "string" &&
            typeof message.id === "string",
        )
      : [];
    return { sessionId: parsed.sessionId ?? null, messages: messages.slice(-MAX_STORED_MESSAGES) };
  } catch {
    return { sessionId: null, messages: [] };
  }
}

function storeChat(chat: StoredChat): void {
  try {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ ...chat, messages: chat.messages.slice(-MAX_STORED_MESSAGES) }),
    );
  } catch {
    // Keeping the conversation in React state is sufficient when storage is unavailable.
  }
}

export function useChat() {
  const initial = useRef<StoredChat | null>(null);
  if (initial.current === null) initial.current = readStoredChat();

  const [sessionId, setSessionId] = useState<string | null>(initial.current.sessionId);
  const [messages, setMessages] = useState<ChatMessage[]>(initial.current.messages);
  const [status, setStatus] = useState<ChatStatus>(initial.current.sessionId ? "ready" : "connecting");
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const sessionRef = useRef(sessionId);
  const sessionPromiseRef = useRef<Promise<string> | null>(null);

  useEffect(() => {
    sessionRef.current = sessionId;
    storeChat({ sessionId, messages });
  }, [messages, sessionId]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const createSession = useCallback((): Promise<string> => {
    if (sessionPromiseRef.current) return sessionPromiseRef.current;
    setStatus("connecting");
    setError(null);
    const pending = (async () => {
      try {
        const response = await chatApi.createSession();
        if (mounted.current) {
          sessionRef.current = response.session_id;
          setSessionId(response.session_id);
          setStatus("ready");
        }
        return response.session_id;
      } catch (reason) {
        if (mounted.current) {
          setError(errorMessage(reason));
          setStatus("error");
        }
        throw reason;
      } finally {
        sessionPromiseRef.current = null;
      }
    })();
    sessionPromiseRef.current = pending;
    return pending;
  }, []);

  useEffect(() => {
    if (!sessionRef.current) void createSession().catch(() => undefined);
  }, [createSession]);

  const submit = useCallback(
    async (rawMessage: string, existingMessage?: ChatMessage) => {
      const content = rawMessage.trim();
      if (!content || status === "sending" || status === "connecting") return;

      const userMessage: ChatMessage =
        existingMessage ?? {
          id: createClientId(),
          requestId: createClientId(),
          role: "user",
          content,
          createdAt: new Date().toISOString(),
          delivery: "sent",
        };

      if (existingMessage) {
        setMessages((current) =>
          current.map((message) =>
            message.id === existingMessage.id ? { ...message, delivery: "sent" } : message,
          ),
        );
      } else {
        setMessages((current) => [...current, userMessage]);
      }
      setStatus("sending");
      setError(null);

      try {
        let activeSession = sessionRef.current ?? (await createSession());
        let response;
        try {
          response = await chatApi.send(
            { session_id: activeSession, message: content },
            userMessage.requestId ?? userMessage.id,
          );
        } catch (reason) {
          if (!(reason instanceof ApiError) || ![404, 410].includes(reason.status)) throw reason;
          activeSession = await createSession();
          response = await chatApi.send(
            { session_id: activeSession, message: content },
            userMessage.requestId ?? userMessage.id,
          );
        }

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
        }
      } catch (reason) {
        if (mounted.current) {
          setMessages((current) =>
            current.map((message) =>
              message.id === userMessage.id ? { ...message, delivery: "failed" } : message,
            ),
          );
          setError(errorMessage(reason));
          setStatus("error");
        }
      }
    },
    [createSession, status],
  );

  const retryLast = useCallback(() => {
    const failedMessage = [...messages]
      .reverse()
      .find((message) => message.role === "user" && message.delivery === "failed");
    if (failedMessage) void submit(failedMessage.content, failedMessage);
    else void createSession().catch(() => undefined);
  }, [createSession, messages, submit]);

  const reset = useCallback(async () => {
    const oldSession = sessionRef.current;
    sessionRef.current = null;
    setSessionId(null);
    setMessages([]);
    setError(null);
    try {
      if (oldSession) await chatApi.reset(oldSession);
    } catch {
      // Reset locally even if an expired server-side session is already gone.
    }
    await createSession();
  }, [createSession]);

  return {
    messages,
    status,
    error,
    isBusy: status === "sending" || status === "connecting",
    send: (message: string) => submit(message),
    retryLast,
    reset,
    reconnect: createSession,
  };
}
