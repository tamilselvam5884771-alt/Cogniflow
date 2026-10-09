import React from 'react';
import { FormattedMessage } from '../utils/formatMarkdown';

export function ChatMessage({ message, onOpenSource }) {
  const isUser = message.role === 'user';

  // Check if assistant reply indicates insufficient evidence
  const isInsufficientEvidence =
    !isUser &&
    (message.isNotice ||
      (message.content &&
        message.content.includes('does not provide enough information')) ||
      (message.sources && message.sources.length === 0));

  return (
    <div className={`message-row ${isUser ? 'message-row-user' : 'message-row-assistant'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🏛️'}
      </div>

      <div className="message-content-wrapper">
        <div className="message-header-meta">
          <span className="message-author">{isUser ? 'You' : 'Handbook Assistant'}</span>
          {message.timestamp && (
            <span className="message-timestamp">{message.timestamp}</span>
          )}
        </div>

        <div className={`message-bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
          {isUser ? (
            <p className="user-text">{message.content}</p>
          ) : (
            <>
              {isInsufficientEvidence && (
                <div className="evidence-notice-banner">
                  <span className="notice-icon">ℹ️</span>
                  <div className="notice-text">
                    <strong>Handbook Notice:</strong> This question could not be answered with certainty from the official college handbook. Institutional policies are not guessed or assumed.
                  </div>
                </div>
              )}

              <FormattedMessage content={message.content} />

              {/* Source citations */}
              {message.sources && message.sources.length > 0 && (
                <div className="citations-container">
                  <div className="citations-header">
                    <span className="citations-title">Verified Handbook Sources:</span>
                    <span className="citations-hint">Click page to view original text</span>
                  </div>
                  <div className="citations-list">
                    {message.sources.map((src, idx) => {
                      const matchPct = src.score ? Math.round(src.score * 100) : null;
                      return (
                        <button
                          key={src.chunk_id || idx}
                          type="button"
                          className="citation-pill"
                          onClick={() => onOpenSource(src)}
                          title={`Click to view extracted excerpt from Page ${src.page_number}`}
                        >
                          <span className="citation-pill-icon">📄</span>
                          <span className="citation-pill-page">Page {src.page_number}</span>
                          {matchPct !== null && (
                            <span className="citation-pill-match">{matchPct}% match</span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
