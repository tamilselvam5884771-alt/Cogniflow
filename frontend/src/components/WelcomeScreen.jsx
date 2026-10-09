import React from 'react';

const SUGGESTED_QUESTIONS = [
  {
    category: 'Attendance',
    icon: '📅',
    question: 'What is the attendance requirement for appearing in semester examinations?',
  },
  {
    category: 'Leave Policy',
    icon: '🌴',
    question: 'What are the rules regarding leave?',
  },
  {
    category: 'Examinations',
    icon: '📝',
    question: 'What are the examination eligibility requirements?',
  },
  {
    category: 'Campus Rules',
    icon: '📱',
    question: 'What are the rules regarding mobile phone usage on campus?',
  },
  {
    category: 'Hostel Policy',
    icon: '🏠',
    question: 'What are the hostel timings, curfew hours, and outing rules?',
  },
  {
    category: 'Discipline',
    icon: '🛡️',
    question: 'What are the institutional penalties and policies regarding anti-ragging?',
  },
];

export function WelcomeScreen({ onSelectQuestion }) {
  return (
    <div className="welcome-container">
      <div className="welcome-hero">
        <div className="hero-emblem">🏛️</div>
        <h1 className="hero-title">College Rules Assistant</h1>
        <p className="hero-description">
          Ask questions about institutional policies, examinations, attendance requirements,
          faculty/student leave, and code of conduct. Answers are strictly grounded in your official college handbook.
        </p>

        <div className="hero-pills">
          <span className="hero-pill">
            <span className="dot teal-dot"></span>
            KSRCE Handbook 2024–2025
          </span>
          <span className="hero-pill">
            <span className="dot teal-dot"></span>
            Verifiable Page Citations
          </span>
          <span className="hero-pill">
            <span className="dot teal-dot"></span>
            Hallucination-Protected RAG
          </span>
        </div>
      </div>

      <div className="suggestions-section">
        <h2 className="suggestions-heading">Suggested Questions</h2>
        <div className="suggestions-grid">
          {SUGGESTED_QUESTIONS.map((item, idx) => (
            <button
              key={idx}
              className="suggestion-card"
              onClick={() => onSelectQuestion(item.question)}
              type="button"
            >
              <div className="suggestion-card-header">
                <span className="suggestion-icon">{item.icon}</span>
                <span className="suggestion-category">{item.category}</span>
              </div>
              <p className="suggestion-text">{item.question}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
