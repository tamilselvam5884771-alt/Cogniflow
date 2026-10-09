import React, { useState, useEffect, useRef } from 'react';
import { WelcomeScreen } from './components/WelcomeScreen';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { SourceModal } from './components/SourceModal';
import { sendChatMessage, getHealth } from './services/api';
import './App.css';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [activeSource, setActiveSource] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [serverError, setServerError] = useState(null);

  const messagesEndRef = useRef(null);

  // Check backend connectivity on mount
  useEffect(() => {
    checkBackendHealth();
  }, []);

  const checkBackendHealth = async () => {
    try {
      const data = await getHealth();
      setHealthStatus(data);
      setServerError(null);
    } catch (err) {
      console.warn('Backend currently unreachable:', err);
      setHealthStatus({ status: 'offline', pdf_indexed: false });
    }
  };

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleNewChat = () => {
    setMessages([]);
    setSessionId(null);
    setServerError(null);
    setInput('');
  };

  const handleSendMessage = async (textToSend = null) => {
    const text = (textToSend || input).trim();
    if (!text || isLoading) return;

    setServerError(null);
    setInput('');

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Add user message to UI immediately
    const userMessageId = `user-${Date.now()}`;
    const newMessages = [
      ...messages,
      {
        id: userMessageId,
        role: 'user',
        content: text,
        timestamp: timeStr,
      },
    ];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(text, sessionId);

      // Preserve session_id returned by backend
      if (response.session_id) {
        setSessionId(response.session_id);
      }

      const assistantMessageId = `assistant-${Date.now()}`;
      setMessages([
        ...newMessages,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: response.reply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          sources: response.sources || [],
        },
      ]);
    } catch (err) {
      console.error('Chat query failed:', err);
      let userFriendlyMessage = 'Failed to generate answer from the handbook.';
      if (err.isNetworkError) {
        userFriendlyMessage =
          'Unable to connect to the backend server. Please verify the FastAPI service is active.';
      } else if (err.status === 503) {
        userFriendlyMessage =
          'The College Rules service is currently initializing or temporarily busy. Please try again in a few moments.';
      } else if (err.message) {
        userFriendlyMessage = err.message;
      }

      setServerError(userFriendlyMessage);

      // Add error card into the chat timeline
      setMessages([
        ...newMessages,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Service Notice:** ${userFriendlyMessage}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          sources: [],
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-shell">
      {/* Top Navigation Bar */}
      <header className="app-header">
        <div className="header-brand">
          <div className="header-logo">🏛️</div>
          <div className="header-text-group">
            <h1 className="header-title">College Rules Assistant</h1>
            <div className="header-status-badge">
              <span
                className={`status-dot ${
                  healthStatus?.status === 'ok' ? 'status-online' : 'status-pending'
                }`}
              ></span>
              <span className="status-label">
                {healthStatus?.status === 'ok'
                  ? `Handbook Active (${healthStatus.total_chunks} Chunks)`
                  : 'FastAPI Backend Ready'}
              </span>
            </div>
          </div>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="new-chat-btn"
            onClick={handleNewChat}
            title="Start a new conversation session"
          >
            <span className="new-chat-icon">↺</span>
            <span className="new-chat-text">New Chat</span>
          </button>
        </div>
      </header>

      {/* Main Conversation Canvas */}
      <main className="chat-canvas">
        {serverError && (
          <div className="global-error-toast" role="alert">
            <span className="toast-icon">⚠️</span>
            <span className="toast-message">{serverError}</span>
            <button
              type="button"
              className="toast-dismiss-btn"
              onClick={() => setServerError(null)}
              aria-label="Dismiss error notice"
            >
              ✕
            </button>
          </div>
        )}

        {messages.length === 0 ? (
          <WelcomeScreen onSelectQuestion={(q) => handleSendMessage(q)} />
        ) : (
          <div className="messages-stream">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onOpenSource={(src) => setActiveSource(src)}
              />
            ))}

            {isLoading && (
              <div className="message-row message-row-assistant">
                <div className="message-avatar">🏛️</div>
                <div className="message-content-wrapper">
                  <div className="message-header-meta">
                    <span className="message-author">Handbook Assistant</span>
                  </div>
                  <div className="message-bubble bubble-assistant loading-bubble">
                    <div className="loading-state-content">
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                      <span className="loading-hint-text">
                        Searching handbook & validating rules...
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Floating or Docked Input Bar */}
      <footer className="chat-footer-dock">
        <ChatInput
          input={input}
          setInput={setInput}
          onSend={() => handleSendMessage()}
          isLoading={isLoading}
        />
      </footer>

      {/* Citation Detail Modal */}
      {activeSource && (
        <SourceModal
          source={activeSource}
          onClose={() => setActiveSource(null)}
        />
      )}
    </div>
  );
}
