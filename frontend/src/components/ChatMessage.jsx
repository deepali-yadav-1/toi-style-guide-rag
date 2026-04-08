export function ChatMessage({ message, onOpenSources, onCopyResponse, copied }) {
  const isAssistant = message.role === "assistant";
  const hasSources = isAssistant && Array.isArray(message.sources) && message.sources.length > 0;
  const hasContent = Boolean(message.content?.trim());

  return (
    <article className={`message ${isAssistant ? "assistant" : "user"}`}>
      <div className="message-meta">
        <span>{isAssistant ? "TOI Assistant" : "You"}</span>
      </div>
      <div className={`message-bubble ${isAssistant && !hasContent ? "is-streaming" : ""}`}>
        {hasContent ? <p>{message.content}</p> : <div className="streaming-placeholder" aria-hidden="true" />}
      </div>
      {isAssistant && hasContent ? (
        <div className="message-actions">
          {hasSources ? (
            <button
              className="source-trigger"
              type="button"
              onClick={() => onOpenSources(message)}
            >
              Sources
            </button>
          ) : null}
          <button
            className="source-trigger"
            type="button"
            onClick={() => onCopyResponse(message)}
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      ) : null}
    </article>
  );
}
