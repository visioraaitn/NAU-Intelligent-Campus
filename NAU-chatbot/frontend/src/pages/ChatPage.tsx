import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { Icon } from "../components/Icon";
import { CHAT_MESSAGE_MAX_LENGTH } from "../config/env";
import { useChat } from "../features/chat/useChat";
import { useOnlineStatus } from "../hooks/useOnlineStatus";
import { formatDateTime } from "../utils/format";

const suggestions = [
  "Quelles formations propose l’IIT ?",
  "Quelle filière correspond à mon profil ?",
  "Quels sont les frais d’inscription ?",
];

export function ChatPage() {
  const { messages, status, error, isBusy, send, retryLast, reset } = useChat();
  const online = useOnlineStatus();
  const [input, setInput] = useState("");
  const [resetOpen, setResetOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const latestAnswerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const previousMessageCount = useRef(messages.length);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
    const newest = messages[messages.length - 1];
    if (messages.length > previousMessageCount.current && newest?.role === "assistant") {
      latestAnswerRef.current?.focus({ preventScroll: true });
    }
    previousMessageCount.current = messages.length;
  }, [messages]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 144)}px`;
  }, [input]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const message = input.trim();
    if (!message || isBusy || !online) return;
    setInput("");
    void send(message);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  const handleReset = async () => {
    setResetting(true);
    try {
      await reset();
      setResetOpen(false);
      textareaRef.current?.focus();
    } catch {
      // useChat already exposes the safe reconnect error in the live region.
    } finally {
      setResetting(false);
    }
  };

  return (
    <main className="chat-page" id="main-content">
      <section className="chat-card" aria-labelledby="chat-title">
        <div className="chat-card__topbar">
          <div className="assistant-identity">
            <span className="assistant-avatar" aria-hidden="true"><Icon name="sparkles" /></span>
            <div>
              <h1 id="chat-title">Assistant IIT</h1>
              <span className="availability">
                <span className={`availability__dot ${online ? "" : "availability__dot--offline"}`} />
                {online ? "Disponible" : "Hors connexion"}
              </span>
            </div>
          </div>
          <button
            className="button button--ghost button--compact"
            type="button"
            onClick={() => setResetOpen(true)}
            disabled={messages.length === 0 || resetting}
          >
            <Icon name="refresh" />
            <span>Nouvelle discussion</span>
          </button>
        </div>

        {!online && (
          <div className="connection-banner" role="status">
            Vous êtes hors connexion. Votre discussion reste disponible sur cet appareil.
          </div>
        )}

        <div className="conversation" role="log" aria-live="polite" aria-relevant="additions text">
          {messages.length === 0 ? (
            <div className="chat-welcome">
              <span className="welcome-icon" aria-hidden="true"><Icon name="chat" /></span>
              <span className="eyebrow">Orientation & admissions</span>
              <h2>Salut 🙂 Qu’est-ce que tu aimerais savoir sur les formations à l’IIT&nbsp;?</h2>
              <p>
                Posez vos questions sur les formations, les spécialisations, l’admission ou les frais de scolarité.
              </p>
              <div className="suggestions" aria-label="Questions suggérées">
                {suggestions.map((suggestion) => (
                  <button
                    className="suggestion"
                    type="button"
                    key={suggestion}
                    disabled={isBusy || !online}
                    onClick={() => void send(suggestion)}
                  >
                    {suggestion}
                    <Icon name="chevron-right" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((message, index) => {
                const isLatestAnswer =
                  message.role === "assistant" &&
                  !messages.slice(index + 1).some((next) => next.role === "assistant");
                return (
                  <article
                    className={`message message--${message.role}`}
                    key={message.id}
                    ref={isLatestAnswer ? latestAnswerRef : undefined}
                    tabIndex={isLatestAnswer ? -1 : undefined}
                    aria-label={message.role === "assistant" ? "Réponse de l’assistant" : "Votre message"}
                  >
                    {message.role === "assistant" && (
                      <span className="message__avatar" aria-hidden="true"><Icon name="sparkles" /></span>
                    )}
                    <div className="message__content">
                      <p>{message.content}</p>
                      <span className="message__meta">
                        {formatDateTime(message.createdAt)}
                        {message.delivery === "failed" && " · Non envoyé"}
                      </span>
                    </div>
                  </article>
                );
              })}
              {status === "sending" && (
                <div className="message message--assistant" role="status" aria-label="L’assistant prépare sa réponse">
                  <span className="message__avatar" aria-hidden="true"><Icon name="sparkles" /></span>
                  <div className="typing-indicator" aria-hidden="true"><span /><span /><span /></div>
                  <span className="sr-only">L’assistant prépare sa réponse…</span>
                </div>
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {error && (
          <div className="chat-error" role="alert">
            <span>{error}</span>
            <button className="button button--ghost button--compact" type="button" onClick={retryLast} disabled={isBusy}>
              <Icon name="refresh" /> Réessayer
            </button>
          </div>
        )}

        <form className="composer" onSubmit={submit}>
          <label className="sr-only" htmlFor="chat-message">Votre message</label>
          <textarea
            ref={textareaRef}
            id="chat-message"
            maxLength={CHAT_MESSAGE_MAX_LENGTH}
            placeholder={status === "connecting" ? "Connexion à l’assistant…" : "Écrivez votre question…"}
            rows={1}
            value={input}
            disabled={status === "connecting"}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="send-button"
            type="submit"
            disabled={!input.trim() || isBusy || !online}
            aria-label="Envoyer le message"
          >
            {isBusy ? <span className="spinner spinner--small" aria-hidden="true" /> : <Icon name="send" />}
          </button>
          <div className="composer__hint">
            <span>Entrée pour envoyer · Maj + Entrée pour une nouvelle ligne</span>
            <span className={input.length > CHAT_MESSAGE_MAX_LENGTH * 0.9 ? "text-warning" : ""}>
              {input.length}/{CHAT_MESSAGE_MAX_LENGTH}
            </span>
          </div>
        </form>
      </section>

      <ConfirmDialog
        open={resetOpen}
        title="Nouvelle discussion"
        message="La discussion affichée sera effacée de cet appareil. Cette action est irréversible."
        confirmLabel="Recommencer"
        busy={resetting}
        destructive
        onCancel={() => setResetOpen(false)}
        onConfirm={() => void handleReset()}
      />
    </main>
  );
}
