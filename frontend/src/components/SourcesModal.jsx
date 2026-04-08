export function SourcesModal({ message, onClose }) {
  if (!message) {
    return null;
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal-panel"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="sources-modal-title"
      >
        <div className="modal-header">
          <div>
            <p className="section-label">Retrieved context</p>
            <h3 id="sources-modal-title">Sources for this answer</h3>
          </div>
          <button className="modal-close" type="button" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="modal-content">
          <p className="modal-answer">{message.content}</p>
          <ul className="source-list">
            {message.sources.map((source) => (
              <li key={source.id} className="source-item">
                <div className="source-header">
                  <strong>{source.document_name}</strong>
                  <span>p. {source.page_number}</span>
                </div>
                <p>{source.content}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
