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
  "Explorer les formations",
  "Vérifier mon admissibilité",
  "Consulter les frais",
  "Préinscription",
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
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
    previousMessageCount.current = messages.length;
  }, [messages]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 144)}px`;
  }, [input]);

  useEffect(() => {
    if (status !== "ready") return;
    const focusTimer = window.setTimeout(() => {
      textareaRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(focusTimer);
  }, [status, conversationId]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const message = input.trim();
    if (!message || isBusy || !online) return;
    setInput("");
    requestAnimationFrame(() => textareaRef.current?.focus());
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
    <div className="admin-shell chat-shell">
      <a className="skip-link" href="#chat-content">Aller au contenu</a>

      {user && (
        <ConversationSidebar
          conversations={history.items}
          activeId={conversationId}
          user={user}
          open={sidebarOpen}
          hasMore={history.items.length < history.total}
          loading={history.loading}
          onClose={() => setSidebarOpen(false)}
          onNew={() => {
            void reset();
            navigate("/chat");
            setSidebarOpen(false);
          }}
          onRename={history.rename}
          onDelete={(item) => setDeleteTarget(item)}
          onLoadMore={history.loadMore}
          onLogout={() => void handleLogout()}
        />
      )}

      <div className="admin-main chat-main">
        <header className="admin-topbar chat-topbar">
          <button
            className="icon-button admin-menu-button"
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Ouvrir le menu"
          >
            <Icon name="menu" />
          </button>
          <div className="admin-topbar__title">
            <span>Assistant</span>
            <strong>Assistant IIT</strong>
          </div>
          {user && (
            <div className="admin-user" aria-label="Session utilisateur">
              <span className="admin-user__avatar" aria-hidden="true">
                {user.name.slice(0, 1).toUpperCase()}
              </span>
              <span>
                <strong>{user.name}</strong>
                <small>{user.role === "ADMIN" ? "Administrateur" : "Utilisateur"}</small>
              </span>
            </div>
          )}
        </header>

        {!online && (
          <div className="connection-banner" role="status">
            Connexion interrompue. L’envoi de messages est temporairement indisponible.
          </div>
        )}

        <main className="chat-content-area" id="chat-content">
          <div className="conversation" role="log" aria-live="polite" aria-relevant="additions text">
            <div className="chat-centered-container">
              {messages.length === 0 ? (
                <ChatWelcome
                  suggestions={suggestions}
                  disabled={isBusy || !online}
                  onSelect={(suggestion) => void send(suggestion)}
                />
              ) : (
                <div className="message-list">
                  {messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
                  ))}
                  {status === "sending" && <ChatLoadingMessage />}
                  <div ref={endRef} />
                </div>
              )}
            </div>
          </div>

          {error && (
            <div className="chat-error-wrapper">
              <div className="chat-error" role="alert">
                <span>Impossible d’obtenir une réponse.</span>
                <button
                  className="button button--ghost button--compact"
                  type="button"
                  onClick={retryLast}
                  disabled={isBusy}
                >
                  <Icon name="refresh" /> Réessayer
                </button>
              </div>
            </div>
          )}

          <div className="composer-wrapper">
            <div className="chat-centered-container">
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
                    {voice.status === "transcribing" ? (
                      <span className="spinner spinner--small" aria-hidden="true" />
                    ) : (
                      <Icon name={voice.status === "recording" ? "stop" : "microphone"} />
                    )}
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
                    {voice.status === "recording" && (
                      <>
                        <i className="recording-dot" aria-hidden="true" /> Enregistrement en cours — recliquez pour arrêter
                      </>
                    )}
                    {voice.status === "transcribing" && "Transcription en cours…"}
                    {(voice.status === "idle" || voice.status === "error") && (
                      "Entrée pour envoyer · Maj + Entrée pour une nouvelle ligne"
                    )}
                  </span>
                  <span className={input.length > CHAT_MESSAGE_MAX_LENGTH * 0.9 ? "text-warning" : ""}>
                    {input.length}/{CHAT_MESSAGE_MAX_LENGTH}
                  </span>
                </div>
              </form>
              <p className="chat-disclaimer">
                Les réponses sont indicatives. Vérifiez les informations importantes auprès de l’IIT.
              </p>
            </div>
          </div>
        </main>
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Supprimer cette conversation ?"
        message={deleteTarget ? `« ${deleteTarget.title} » sera supprimée définitivement.` : ""}
        confirmLabel="Supprimer"
        destructive
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => void handleDelete()}
      />
    </div>
  );
}
