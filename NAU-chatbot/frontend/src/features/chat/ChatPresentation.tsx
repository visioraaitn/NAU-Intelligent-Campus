import { Icon } from "../../components/Icon";
import type { ChatMessage as ChatMessageType } from "../../types/chat";
import { formatDateTime } from "../../utils/format";
import { ChatMessageContent } from "./ChatMessageContent";

interface ChatWelcomeProps {
  suggestions: string[];
  disabled: boolean;
  onSelect: (suggestion: string) => void;
}

export function ChatWelcome({ suggestions, disabled, onSelect }: ChatWelcomeProps) {
  return (
    <div className="chat-welcome">
      <span className="welcome-badge">Assistant IIT</span>
      <h2>Comment puis-je vous aider&nbsp;?</h2>
      <p>Posez votre question sur les formations, l’admission, l’orientation ou les frais.</p>
      <div className="suggestions" aria-label="Questions suggérées">
        {suggestions.map((suggestion) => (
          <button
            className="suggestion"
            type="button"
            key={suggestion}
            disabled={disabled}
            onClick={() => onSelect(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  return (
    <article
      className={`message message--${message.role} ${message.delivery === "failed" ? "message--failed" : ""}`}
      aria-label={message.role === "assistant" ? "Réponse de l’assistant" : "Votre message"}
    >
      {message.role === "assistant" && (
        <span className="message__avatar" aria-hidden="true"><Icon name="sparkles" /></span>
      )}
      <div className="message__content">
        <ChatMessageContent content={message.content} />
        <span className="message__meta">
          {formatDateTime(message.createdAt)}
          {message.delivery === "failed" && " · Non envoyé"}
        </span>
      </div>
    </article>
  );
}

export function ChatLoadingMessage() {
  return (
    <div className="message message--assistant message--loading" role="status" aria-label="L’assistant prépare sa réponse">
      <span className="message__avatar" aria-hidden="true"><Icon name="sparkles" /></span>
      <div className="typing-indicator">
        <span className="typing-indicator__label">L’assistant prépare sa réponse</span>
        <span className="typing-indicator__dots" aria-hidden="true"><i /><i /><i /></span>
      </div>
    </div>
  );
}
