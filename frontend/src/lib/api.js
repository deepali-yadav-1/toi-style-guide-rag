const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function parseResponse(response, fallbackMessage) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || fallbackMessage);
  }

  return response.json();
}

export async function sendChatMessage(payload) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseResponse(response, "Chat request failed.");
}

export async function streamChatMessage(payload, handlers) {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Streaming chat request failed.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const rawEvent of events) {
      const lines = rawEvent.split("\n");
      const eventLine = lines.find((line) => line.startsWith("event:"));
      const dataLine = lines.find((line) => line.startsWith("data:"));
      if (!eventLine || !dataLine) {
        continue;
      }

      const eventName = eventLine.slice(6).trim();
      const payloadData = JSON.parse(dataLine.slice(5).trim());

      if (eventName === "token") {
        handlers.onToken?.(payloadData.token);
      } else if (eventName === "sources") {
        handlers.onSources?.(payloadData.sources, payloadData.retrieved_at);
      } else if (eventName === "done") {
        handlers.onDone?.();
      } else if (eventName === "error") {
        throw new Error(payloadData.detail || "Streaming chat failed.");
      }
    }
  }
}

export async function fetchStatus() {
  const response = await fetch(`${API_BASE_URL}/status`);
  return parseResponse(response, "Failed to load system status.");
}

export async function triggerIngestion(payload = { reset_existing: false }) {
  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseResponse(response, "Failed to ingest documents.");
}
