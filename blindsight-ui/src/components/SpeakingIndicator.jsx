import React from 'react';
import './SpeakingIndicator.css';

export default function SpeakingIndicator({ text }) {
  return (
    <div className="speaking-indicator">
      <div className="wave">
        {[0, 0.08, 0.16, 0.24, 0.32].map((delay, i) => (
          <span key={i} className="wave-bar" style={{ animationDelay: `${delay}s` }} />
        ))}
      </div>
      <span className="speaking-text">{text || 'SPEAKING ALOUD'}</span>
    </div>
  );
}
