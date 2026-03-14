import React, { useState, useRef } from 'react';
import { useBlindSight } from '../context/BlindSightContext';
import SpeakingIndicator from '../components/SpeakingIndicator';
import RouteMap from '../components/RouteMap';
import useNavigation from '../hooks/useNavigation';
import './AssistantScreen.css';

// Tools that can use live location automatically
const LOCATION_AUTO_TOOLS = new Set(['weather', 'forecast', 'emergency', 'headlines']);

// Tool IDs must match the server's mcp_request handler in server/main.py
const TOOLS = [
  { id: 'navigate',     name: 'Navigation',  desc: 'Turn-by-turn walking directions', icon: '🧭', color: 'cyan',   placeholder: 'Destination, e.g. Red Fort',          needsInput: true  },
  { id: 'weather',      name: 'Weather',      desc: 'Current conditions & forecast',   icon: '🌤', color: 'blue',   placeholder: 'City name (auto from GPS)',            needsInput: false },
  { id: 'headlines',    name: 'Headlines',    desc: 'Top news by country',             icon: '📰', color: 'amber',  placeholder: 'Country code (auto from GPS)',         needsInput: false },
  { id: 'emergency',    name: 'Emergency',    desc: 'Local emergency numbers',         icon: '🆘', color: 'red',    placeholder: 'Location (auto from GPS)',             needsInput: false },
  { id: 'safety_tips',  name: 'Safety Tips',  desc: 'Context-specific walking advice', icon: '🛡️', color: 'green',  placeholder: 'walking / crossing / night',           needsInput: true  },
  { id: 'search_news',  name: 'Search News',  desc: 'Search news by keyword',          icon: '🔍', color: 'purple', placeholder: 'e.g. traffic accidents Delhi',         needsInput: true  },
];

function ToolGrid({ activeTool, onSelect }) {
  return (
    <div className="tool-grid">
      {TOOLS.map(t => (
        <button
          key={t.id}
          className={`tool-card ${t.color} ${activeTool === t.id ? 'active' : ''}`}
          onClick={() => onSelect(t.id)}
        >
          <div className={`tool-icon-wrap ${t.color}`}>{t.icon}</div>
          <div className="tool-name">{t.name}</div>
          <div className="tool-desc">{t.desc}</div>
        </button>
      ))}
    </div>
  );
}

function ResultCard({ result, loading, speaking, userLocation }) {
  // Navigation checkpoint tracker — only active when we have a nav result
  const navSteps = (result?.steps && Array.isArray(result.steps)) ? result.steps : null;
  const { activeStep, arrived, distToNext } = useNavigation(navSteps, userLocation);

  if (loading) {
    return (
      <div className="result-card loading">
        <div className="result-label">PROCESSING</div>
        <div className="result-spinner">
          {[0,1,2,3].map(i => (
            <span key={i} className="spinner-dot" style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    );
  }
  if (!result) return null;
  if (result.error) {
    return (
      <div className="result-card error">
        <div className="result-label">ERROR</div>
        <div className="result-body">{result.error}</div>
      </div>
    );
  }

  // Navigation result
  if (navSteps) {
    return (
      <div className="result-card" style={{ animation: 'slide-up 0.25s ease' }}>
        <div className="result-label">NAVIGATION</div>
        <div className="result-summary">{result.summary}</div>

        {/* Active step banner */}
        {!arrived ? (
          <div className="nav-active-banner">
            <span className="nav-active-icon">🔊</span>
            <div className="nav-active-body">
              <span className="nav-active-instruction">{navSteps[activeStep]?.instruction}</span>
              {distToNext !== null && (
                <span className="nav-active-dist">{distToNext}m to next turn</span>
              )}
            </div>
          </div>
        ) : (
          <div className="nav-arrived-banner">🏁 You have arrived!</div>
        )}

        <RouteMap
          origin={result.origin}
          destination={result.destination}
          steps={navSteps}
          geometry={result.geometry}
          activeStep={activeStep}
        />

        <div className="nav-steps">
          {navSteps.map((step, i) => (
            <div
              key={i}
              className={`nav-step ${i === activeStep ? 'active' : ''} ${i < activeStep ? 'done' : ''}`}
            >
              <span className="nav-step-num">
                {i < activeStep ? '✓' : i + 1}
              </span>
              <div className="nav-step-body">
                <span className="nav-step-instruction">{step.instruction}</span>
                <span className="nav-step-meta">{step.distance} · {step.duration}</span>
              </div>
            </div>
          ))}
        </div>
        {speaking && <SpeakingIndicator />}
      </div>
    );
  }

  const displayText = result.spoken_summary || result.result || result.message || JSON.stringify(result, null, 2);
  return (
    <div className="result-card" style={{ animation: 'slide-up 0.25s ease' }}>
      <div className="result-label">RESPONSE</div>
      <div className="result-body">{displayText}</div>
      {speaking && <SpeakingIndicator />}
    </div>
  );
}

export default function AssistantScreen() {
  const { activeTool, setActiveTool, callMCPTool, mcpResult, mcpLoading, speaking, userLocation } = useBlindSight();
  const [query, setQuery] = useState('');
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  const tool       = TOOLS.find(t => t.id === activeTool) || TOOLS[0];
  const isNavigate = activeTool === 'navigate';
  const isAutoLoc  = LOCATION_AUTO_TOOLS.has(activeTool);
  const hasGPS     = !!userLocation;

  // Build the input string to send for location-aware tools
  const buildInput = () => {
    if (isNavigate) {
      return `${userLocation.lat},${userLocation.lng} to ${query.trim()}`;
    }
    if (isAutoLoc && hasGPS) {
      // Send lat,lng — server will reverse geocode as needed
      return `${userLocation.lat},${userLocation.lng}`;
    }
    return query.trim();
  };

  const canSend = () => {
    if (mcpLoading) return false;
    if (isNavigate) return !!query.trim() && hasGPS;
    if (isAutoLoc)  return hasGPS || !!query.trim(); // GPS preferred, manual fallback
    return !!query.trim();
  };

  const handleSend = () => {
    if (!canSend()) return;
    if (isNavigate && !hasGPS) {
      alert('Waiting for GPS location. Please allow location access and try again.');
      return;
    }
    callMCPTool(activeTool, buildInput());
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleSelectTool = (id) => { setActiveTool(id); setQuery(''); };

  const handleVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('Speech recognition not supported. Try Chrome.'); return; }
    if (listening) { recognitionRef.current?.stop(); setListening(false); return; }
    const r = new SR();
    r.lang = 'en-IN'; r.continuous = false; r.interimResults = false;
    r.onresult = (e) => setQuery(e.results[0][0].transcript);
    r.onend    = () => setListening(false);
    r.onerror  = () => setListening(false);
    r.start();
    recognitionRef.current = r;
    setListening(true);
  };

  return (
    <div className="assistant-screen">
      <div className="asst-header">
        <span className="asst-section-label">AI ASSISTANT</span>
        <span className="asst-sub">Select a tool, then speak or type</span>
      </div>

      <ToolGrid activeTool={activeTool} onSelect={handleSelectTool} />

      <div className="input-section">
        <div className="input-label">
          <span className="input-tool-name">{tool.icon} {tool.name}</span>
          <span className="input-hint">Enter key sends</span>
        </div>

        {/* GPS badge — shown for all location-aware tools */}
        {(isNavigate || isAutoLoc) && (
          <div className={`gps-origin-badge ${hasGPS ? 'active' : 'waiting'}`}>
            <span>{hasGPS ? '📍' : '⏳'}</span>
            <span>
              {hasGPS
                ? `GPS: ${userLocation.lat.toFixed(4)}, ${userLocation.lng.toFixed(4)} (±${Math.round(userLocation.accuracy)}m)`
                : 'Waiting for GPS…'}
            </span>
          </div>
        )}

        {/* Auto-location tools: show one-tap send button, optional manual override */}
        {isAutoLoc && !isNavigate ? (
          <div className="auto-loc-section">
            <button
              className="auto-loc-btn"
              onClick={handleSend}
              disabled={!hasGPS || mcpLoading}
            >
              {mcpLoading ? 'Loading…' : `Use my location →`}
            </button>
            <div className="auto-loc-divider"><span>or enter manually</span></div>
            <textarea
              className="asst-input"
              rows={2}
              placeholder={tool.placeholder}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <div className="send-row">
              <button className={`mic-btn ${listening ? 'active' : ''}`} onClick={handleVoice} aria-label="Voice input">🎙</button>
              <button className="send-btn" onClick={() => { if (query.trim()) callMCPTool(activeTool, query.trim()); }} disabled={!query.trim() || mcpLoading}>
                Send →
              </button>
            </div>
          </div>
        ) : (
          <>
            <textarea
              className="asst-input"
              rows={2}
              placeholder={isNavigate ? 'Enter destination, e.g. Red Fort, Delhi' : tool.placeholder}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <div className="send-row">
              <button className={`mic-btn ${listening ? 'active' : ''}`} onClick={handleVoice} aria-label="Voice input">🎙</button>
              <button className="send-btn" onClick={handleSend} disabled={!canSend()}>
                {mcpLoading ? 'Sending…' : 'Send →'}
              </button>
            </div>
          </>
        )}
      </div>

      <ResultCard result={mcpResult} loading={mcpLoading} speaking={speaking} userLocation={userLocation} />
    </div>
  );
}
