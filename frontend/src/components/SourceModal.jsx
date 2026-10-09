import React, { useEffect, useState } from 'react';

export function SourceModal({ source, onClose }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!source) return null;

  const handleCopy = () => {
    if (source.snippet) {
      navigator.clipboard.writeText(source.snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const relevancePercentage = source.score ? Math.round(source.score * 100) : null;

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon">📄</span>
            <div>
              <h3 id="modal-title" className="modal-title">
                Handbook Excerpt — Page {source.page_number}
              </h3>
              <p className="modal-subtitle">
                Official Institutional Handbook (2024–2025)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="modal-close-btn"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        <div className="modal-meta-bar">
          <span className="modal-badge chunk-badge">
            Chunk: {source.chunk_id}
          </span>
          {relevancePercentage !== null && (
            <span className="modal-badge score-badge">
              Relevance: {relevancePercentage}%
            </span>
          )}
        </div>

        <div className="modal-body">
          <div className="modal-label">Extracted Text Content:</div>
          <div className="excerpt-box">
            <pre className="excerpt-text">{source.snippet}</pre>
          </div>
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleCopy}
          >
            {copied ? '✓ Excerpt Copied' : '📋 Copy Excerpt'}
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
