import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { Icon } from "../components/Icon";
import { CHAT_MESSAGE_MAX_LENGTH } from "../config/env";
import { ChatLoadingMessage, ChatMessage, ChatWelcome } from "../features/chat/ChatPresentation";
import { ConversationSidebar } from "../features/chat/ConversationSidebar";
import { useChat } from "../features/chat/useChat";
import { useConversations } from "../features/chat/useConversations";
import { useAuth } from "../features/auth/AuthContext";
import { useVoiceRecorder } from "../features/chat/useVoiceRecorder";
import { useOnlineStatus } from "../hooks/useOnlineStatus";

const suggestions = [
  "Quelles formations propose l’IIT ?",
  "Quelle filière correspond à mon profil ?",
  "Quels sont les frais d’inscription ?",
];

export function ChatPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const history = useConversations();
  const { messages, status, error, isBusy, send, retryLast, reset } = useChat({
    conversationId,
    onConversationCreated: (id) => navigate(`/chat/${id}`, { replace: true }),
    onConversationChanged: history.refresh,
  });
  const online = useOnlineStatus();
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const latestAnswerRef = useRef<HTMLElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const previousMessageCount = useRef(messages.length);
  const appendTranscription = useCallback((text: string) => {
    const transcription = text.trim();
    if (!transcription) return;
    setInput((current) => current.trim() ? `${current.trimEnd()} ${transcription}` : transcription);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);
  const voice = useVoiceRecorder(appendTranscription);

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

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await history.remove(deleteTarget.id);
    if (deleteTarget.id === conversationId) {
      await reset();
      navigate("/chat", { replace: true });
    }
    setDeleteTarget(null);
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <main className="chat-workspace" id="main-content">
      {user && <ConversationSidebar conversations={history.items} activeId={conversationId} user={user} open={sidebarOpen} hasMore={history.items.length < history.total} loading={history.loading} onClose={() => setSidebarOpen(false)} onNew={() => { void reset(); navigate("/chat"); setSidebarOpen(false); }} onRename={history.rename} onDelete={(item) => setDeleteTarget(item)} onLoadMore={history.loadMore} onLogout={() => void handleLogout()} />}
      <div className="chat-page">
      <section className="chat-card" aria-labelledby="chat-title">
        <div className="chat-card__topbar">
          <button className="icon-button chat-history-button" type="button" onClick={() => setSidebarOpen(true)} aria-label="Ouvrir l’historique"><Icon name="menu" /></button>
          <div className="assistant-identity">
            <div>
              <h1 id="chat-title">Assistant IIT</h1>
              <p>Orientation &amp; informations académiques</p>
            </div>
          </div>
          <span className="availability">
            <span className={`availability__dot ${online ? "" : "availability__dot--offline"}`} />
            {online ? "En ligne" : "Hors connexion"}
          </span>
        </div>

        {!online && (
          <div className="connection-banner" role="status">
            Connexion interrompue. L’envoi de messages est temporairement indisponible.
          </div>
        )}

        <div className="conversation" role="log" aria-live="polite" aria-relevant="additions text">
          {messages.length === 0 ? (
            <ChatWelcome
              suggestions={suggestions}
              disabled={isBusy || !online}
              onSelect={(suggestion) => void send(suggestion)}
            />
          ) : (
            <div className="message-list">
              {messages.map((message, index) => {
                const isLatestAnswer =
                  message.role === "assistant" &&
                  !messages.slice(index + 1).some((next) => next.role === "assistant");
                return (
                  <ChatMessage
                    key={message.id}
                    ref={isLatestAnswer ? latestAnswerRef : undefined}
                    message={message}
                    latestAssistantMessage={isLatestAnswer}
                  />
                );
              })}
              {status === "sending" && <ChatLoadingMessage />}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {error && (
          <div className="chat-error" role="alert">
            <span>Impossible d’obtenir une réponse.</span>
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
            placeholder={status === "connecting" ? "Connexion à l’assistant…" : "Posez votre question…"}
            rows={1}
            value={input}
            disabled={status === "connecting"}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div className="composer__actions">
            <button
              className={`voice-button ${voice.status === "recording" ? "voice-button--recording" : ""}`}
              type="button"
              onClick={voice.toggleRecording}
              disabled={voice.status === "transcribing" || (voice.status !== "recording" && (isBusy || !online))}
              aria-label={voice.status === "recording" ? "Arrêter l’enregistrement vocal" : "Démarrer l’enregistrement vocal"}
            >
              {voice.status === "transcribing"
                ? <span className="spinner spinner--small" aria-hidden="true" />
                : <Icon name={voice.status === "recording" ? "stop" : "microphone"} />}
            </button>
            <button
              className="send-button"
              type="submit"
              disabled={!input.trim() || isBusy || !online}
              aria-label="Envoyer le message"
            >
              {isBusy ? <span className="spinner spinner--small" aria-hidden="true" /> : <Icon name="send" />}
            </button>
          </div>
          {voice.error && <div className="voice-feedback voice-feedback--error" role="alert">{voice.error}</div>}
          <div className="composer__hint">
            <span aria-live="polite">
              {voice.status === "recording" && <><i className="recording-dot" aria-hidden="true" /> Enregistrement en cours — recliquez pour arrêter</>}
              {voice.status === "transcribing" && "Transcription en cours…"}
              {(voice.status === "idle" || voice.status === "error") && "Entrée pour envoyer · Maj + Entrée pour une nouvelle ligne"}
            </span>
            <span className={input.length > CHAT_MESSAGE_MAX_LENGTH * 0.9 ? "text-warning" : ""}>
              {input.length}/{CHAT_MESSAGE_MAX_LENGTH}
            </span>
          </div>
        </form>
      </section>
      <p className="chat-disclaimer">Les réponses sont indicatives. Vérifiez les informations importantes auprès de l’IIT.</p>
      </div>

      <ConfirmDialog open={deleteTarget !== null} title="Supprimer cette conversation ?" message={deleteTarget ? `« ${deleteTarget.title} » sera supprimée définitivement.` : ""} confirmLabel="Supprimer" destructive onCancel={() => setDeleteTarget(null)} onConfirm={() => void handleDelete()} />
    </main>
  );
}
