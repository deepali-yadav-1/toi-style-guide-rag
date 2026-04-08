import { useState } from "react";

export function ChatComposer({ disabled, onSend }) {
  const [value, setValue] = useState("");

  function submitMessage(event) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) {
      return;
    }

    onSend(trimmed);
    setValue("");
  }

  return (
    <form className="composer" onSubmit={submitMessage}>
      <textarea
        className="composer-input"
        placeholder="Ask about spelling, usage, punctuation, or newsroom style..."
        value={value}
        onChange={(event) => setValue(event.target.value)}
        rows={1}
        disabled={disabled}
      />
      <button className="composer-button" type="submit" disabled={disabled}>
        Send
      </button>
    </form>
  );
}
