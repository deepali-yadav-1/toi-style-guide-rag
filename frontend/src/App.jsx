import { startTransition, useEffect, useRef, useState } from "react";

import { ChatComposer } from "./components/ChatComposer";
import { ChatMessage } from "./components/ChatMessage";
import { SourcesModal } from "./components/SourcesModal";
import { fetchStatus, streamChatMessage, triggerIngestion } from "./lib/api";


const INITIAL_MESSAGE = {
  id: crypto.randomUUID(),
  role: "assistant",
  content:
    "Ask me anything about the TOI style guide or glossary. I’ll answer from the indexed PDFs and surface the passages I used.",
  sources: [],
};

const SUGGESTED_QUESTIONS = [
  "When should abbreviations be avoided in copy?",
  "What are the main rules for headline writing?",
  "Summarize the guidance on punctuation and clarity",
  "How should foreign words be handled in print style?",
];


export default function App() {
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(null);
  const [statusError, setStatusError] = useState("");
  const [selectedSourcesMessage, setSelectedSourcesMessage] = useState(null);
  const [copiedMessageId, setCopiedMessageId] = useState("");
  const scrollAnchorRef = useRef(null);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    async function loadStatus() {
      try {
        const response = await fetchStatus();
        setStatus(response);
        setStatusError("");
      } catch (requestError) {
        setStatusError(requestError.message);
      }
    }

    loadStatus();
  }, []);

  async function handleSend(query) {
    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
    };
    const assistantMessageId = crypto.randomUUID();
    const streamingAssistantMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      sources: [],
    };
    const historyMessages = [...messages, userMessage];
    setMessages((current) => [...current, userMessage, streamingAssistantMessage]);
    setIsLoading(true);
    setError("");

    try {
      await streamChatMessage({
        query,
        history: historyMessages
          .slice(1)
          .slice(-8)
          .map((message) => ({
            role: message.role,
            content: message.content,
          })),
      }, {
        onToken(token) {
          startTransition(() => {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantMessageId
                  ? { ...message, content: message.content + token }
                  : message
              )
            );
          });
        },
        onSources(sources) {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, sources }
                : message
            )
          );
        },
      });
    } catch (requestError) {
      setMessages((current) =>
        current.filter((message) => message.id !== assistantMessageId)
      );
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleIngest() {
    setIsIngesting(true);
    setError("");

    try {
      const response = await triggerIngestion({ reset_existing: false });
      const summary = response.processed_files
        .map((item) => `${item.document_name}: ${item.chunks_inserted} chunks`)
        .join(" | ");

      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Ingestion complete. ${summary || "No new chunks were inserted."}`,
          sources: [],
        },
      ]);

      const freshStatus = await fetchStatus();
      setStatus(freshStatus);
      setStatusError("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsIngesting(false);
    }
  }

  async function handleCopyResponse(message) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedMessageId(message.id);
      window.setTimeout(() => {
        setCopiedMessageId((current) => (current === message.id ? "" : current));
      }, 1600);
    } catch (copyError) {
      setError("Failed to copy the response.");
    }
  }

  return (
    <>
      <div className="app-shell">
        <aside className="hero-panel">
          <div className="hero-copy">
            <p className="eyebrow">Editorial RAG Workspace</p>
            <h1>TOI style answers grounded in the source PDFs.</h1>
            <p className="hero-text">
              Built for newsroom lookup: quick answers, visible citations, and a
              reading experience that stays calm on desktop and mobile.
            </p>
            <div className="hero-detail">
              <span>{status ? `${status.documents_indexed} documents indexed` : "System status loading"}</span>
              <span>{status ? `${status.chunks_indexed} chunks ready` : "FastAPI + React + Supabase pgvector"}</span>
            </div>
            <div className="hero-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={handleIngest}
                disabled={isIngesting}
              >
                {isIngesting ? "Ingesting PDFs..." : "Ingest PDFs"}
              </button>
            </div>
            {status ? (
              <p className="status-text">
                System status: <strong>{status.status}</strong>
              </p>
            ) : null}
            {statusError ? <p className="status-text error-text">{statusError}</p> : null}
          </div>
        </aside>

        <main className="chat-panel">
          <header className="chat-header chat-header-compact">
            <p className="chat-kicker">TOI Style Assistant</p>
          </header>

          <section className="chat-history">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onOpenSources={setSelectedSourcesMessage}
                onCopyResponse={handleCopyResponse}
                copied={copiedMessageId === message.id}
              />
            ))}
            <div ref={scrollAnchorRef} />
          </section>

          <footer className="chat-footer">
            {error ? <p className="error-banner">{error}</p> : null}
            <div className="suggestions-panel">
              <p className="suggestions-title">Try a question</p>
              <div className="suggestions-list">
                {SUGGESTED_QUESTIONS.map((question) => (
                  <button
                    key={question}
                    className="suggestion-chip"
                    type="button"
                    disabled={isLoading || isIngesting}
                    onClick={() => handleSend(question)}
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
            <ChatComposer disabled={isLoading || isIngesting} onSend={handleSend} />
          </footer>
        </main>
      </div>

      <SourcesModal
        message={selectedSourcesMessage}
        onClose={() => setSelectedSourcesMessage(null)}
      />
    </>
  );
}
