import React from 'react';
import { useBlindSight } from '../context/BlindSightContext';
import SpeakingIndicator from '../components/SpeakingIndicator';
import './RadarScreen.css';

const DIRECTION_LABELS = ['LEFT', 'CENTER', 'RIGHT'];

function CameraFeed({ hazard, heatmapOverlay, heatmap, frameData }) {
  const directionToPos = (dir) => {
    if (!dir) return '50%';
    const d = dir.toLowerCase();
    if (d.includes('left'))  return '25%';
    if (d.includes('right')) return '75%';
    return '50%';
  };

  return (
    <div className="cam-feed">
      {/* Live annotated frame from server */}
      {frameData
        ? <img src={frameData} className="cam-live-img" alt="camera feed" />
        : <div className="cam-grid" />
      }
      <div className="path-zone" />
      <span className="cam-corner tl" /><span className="cam-corner tr" />
      <span className="cam-corner bl" /><span className="cam-corner br" />
      <div className="live-badge">REC</div>

      {/* Overlay hazard box only when no server frame (fallback) */}
      {!frameData && hazard && (
        <div className="hazard-box" style={{ left: directionToPos(hazard.direction) }}>
          <span className="hazard-label">{hazard.label.toUpperCase()}</span>
          <span className="distance-tag">{hazard.distance?.toFixed(1)} m</span>
        </div>
      )}

      {!frameData && !hazard && (
        <div className="no-hazard-msg"><span>PATH CLEAR</span></div>
      )}

      {heatmapOverlay && (
        <div className="heatmap-overlay">
          {['left', 'centerL', 'centerR', 'right'].map(lane => (
            <div key={lane} className={`hl-lane ${heatmap[lane] || 'safe'}`} />
          ))}
        </div>
      )}
    </div>
  );
}

function HeatmapBar({ heatmap }) {
  const lanes = [
    { key: 'left',    label: 'LEFT' },
    { key: 'centerL', label: 'CTR-L' },
    { key: 'centerR', label: 'CTR-R' },
    { key: 'right',   label: 'RIGHT' },
  ];
  return (
    <div className="heatmap-section">
      <div className="heatmap-bars">
        {lanes.map(l => (
          <div key={l.key} className={`heat-bar ${heatmap[l.key] || 'safe'}`} />
        ))}
      </div>
      <div className="heatmap-labels">
        {lanes.map(l => <span key={l.key}>{l.label}</span>)}
      </div>
    </div>
  );
}

function HazardCard({ hazard }) {
  const dir = hazard?.direction?.toLowerCase() || '';
  return (
    <div className={`hazard-card ${hazard ? 'active' : ''}`}>
      <div className="hc-top">
        <span className="hc-section-label">NEAREST HAZARD</span>
        <span className={`hc-badge ${hazard ? 'tracking' : 'idle'}`}>
          {hazard ? 'TRACKING' : 'SCANNING'}
        </span>
      </div>
      <div className="hc-main">{hazard ? hazard.label : 'None detected'}</div>
      <div className="hc-dist">
        {hazard ? `${hazard.distance?.toFixed(1)} metres away` : 'Path is clear'}
      </div>
      <div className="direction-bar">
        {DIRECTION_LABELS.map(d => (
          <div
            key={d}
            className={`dir-pill ${dir.includes(d.toLowerCase()) ? 'active' : ''}`}
          >
            {d}
          </div>
        ))}
      </div>
    </div>
  );
}

function GuidanceStrip({ hazard, sceneDescription, sceneLoading }) {
  const text = sceneLoading
    ? 'Generating scene description…'
    : sceneDescription
    ? sceneDescription
    : hazard
    ? hazard.guidance
    : 'No obstacles detected. Path appears clear ahead.';

  return (
    <div className={`guidance-strip ${hazard && !sceneDescription ? 'warn' : 'safe'}`}>
      {text}
    </div>
  );
}

function ActionButtons({ onDescribeScene, onEmergency, onSafety, sceneLoading }) {
  return (
    <div className="action-grid">
      <button className="act-btn cyan" onClick={onDescribeScene} disabled={sceneLoading}>
        <span className="act-icon-wrap cyan">👁</span>
        <span>{sceneLoading ? 'Loading…' : 'Describe Scene'}</span>
      </button>
      <button className="act-btn blue" onClick={onSafety}>
        <span className="act-icon-wrap blue">🛡️</span>
        <span>Safety Tips</span>
      </button>
      <button className="act-btn red" onClick={onEmergency}>
        <span className="act-icon-wrap red">🆘</span>
        <span>Emergency</span>
      </button>
      <button
        className="act-btn amber"
        onClick={() => document.getElementById('alert-log')?.scrollIntoView({ behavior: 'smooth' })}
      >
        <span className="act-icon-wrap amber">📋</span>
        <span>Alert Log</span>
      </button>
    </div>
  );
}

function AlertLog({ alerts, onClear }) {
  return (
    <div className="alert-log-section" id="alert-log">
      <div className="section-head">
        <span className="section-label">RECENT ALERTS</span>
        <button className="clear-btn" onClick={onClear}>CLEAR</button>
      </div>
      <div className="alert-list">
        {alerts.length === 0 && (
          <div className="alert-empty">No alerts yet</div>
        )}
        {alerts.map(a => (
          <div key={a.id} className="alert-item" style={{ animation: 'slide-up 0.25s ease' }}>
            <span className={`alert-dot ${a.type}`} />
            <span className="alert-text">{a.text}</span>
            <span className="alert-time">{a.ts}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function RadarScreen({ onNavigateTo }) {
  const {
    hazard, alertLog, heatmap, clearAlerts,
    sceneDescription, sceneLoading, requestScene,
    settings, speaking, callMCPTool, setActiveTool,
    frameData,
  } = useBlindSight();

  const handleEmergency = () => {
    setActiveTool('emergency');
    onNavigateTo('assistant');
    setTimeout(() => callMCPTool('emergency', 'India'), 100);
  };

  const handleSafety = () => {
    setActiveTool('safety_tips');
    onNavigateTo('assistant');
    setTimeout(() => callMCPTool('safety_tips', 'walking'), 100);
  };

  return (
    <div className="radar-screen">
      <CameraFeed hazard={hazard} heatmapOverlay={settings.heatmapOverlay} heatmap={heatmap} frameData={frameData} />
      <HeatmapBar heatmap={heatmap} />
      <HazardCard hazard={hazard} />
      <GuidanceStrip hazard={hazard} sceneDescription={sceneDescription} sceneLoading={sceneLoading} />
      {speaking && <div className="speaking-wrap"><SpeakingIndicator /></div>}
      <ActionButtons
        onDescribeScene={requestScene}
        onEmergency={handleEmergency}
        onSafety={handleSafety}
        sceneLoading={sceneLoading}
      />
      <AlertLog alerts={alertLog} onClear={clearAlerts} />
    </div>
  );
}
