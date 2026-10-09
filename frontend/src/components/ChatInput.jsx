import React, { useRef, useEffect } from 'react';

export function ChatInput({ input, setInput, onSend, isLoading }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        onSend();
      }
    }
  };

  const handleInput = (e) => {
    setInput(e.target.value);
    // Auto-grow textarea up to 160px
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  return (
    <div className="input-bar-container">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (input.trim() && !isLoading) onSend();
        }}
        className="input-form"
      >
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={
              isLoading
                ? 'Consulting college handbook...'
                : 'Ask a question about college rules, attendance, leaves, exams...'
            }
            disabled={isLoading}
            className="chat-textarea"
            maxLength={2000}
          />

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="send-button"
            aria-label="Send question"
            title="Press Enter to send, Shift+Enter for newline"
          >
            {isLoading ? (
              <span className="spinner"></span>
            ) : (
              <span className="send-icon">➤</span>
            )}
          </button>
        </div>

        <div className="input-footer">
          <span className="input-hint">
            Press <kbd>Enter ↵</kbd> to send, <kbd>Shift + Enter</kbd> for new line
          </span>
          <span className="input-security-note">
            🛡️ Answers strictly sourced from verified college rules
          </span>
        </div>
      </form>
    </div>
  );
}
