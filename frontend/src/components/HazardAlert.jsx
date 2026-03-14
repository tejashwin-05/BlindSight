import './HazardAlert.css'

function HazardAlert({ data }) {
  const { hazard, direction, distance, confidence, total_hazards, guidance } = data

  if (!hazard) {
    return (
      <div className="hazard-alert safe">
        <div className="safe-indicator">
          <div className="pulse-ring"></div>
          <div className="status-icon">✓</div>
        </div>
        <h2 className="safe-title">All Clear</h2>
        <p className="safe-subtitle">Path is safe to proceed</p>
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-value">{total_hazards}</span>
            <span className="stat-label">Objects Detected</span>
          </div>
        </div>
      </div>
    )
  }

  const urgencyLevel = distance < 1.5 ? 'critical' : distance < 3 ? 'warning' : 'info'
  const directionIcon = direction === 'left' ? '←' : direction === 'right' ? '→' : '↑'

  return (
    <div className={`hazard-alert ${urgencyLevel}`}>
      <div className="alert-badge">{urgencyLevel === 'critical' ? '⚠️ URGENT' : '⚠️ ALERT'}</div>
      
      <div className="hazard-visual">
        <div className="hazard-icon-wrapper">
          <div className="hazard-icon">🚨</div>
        </div>
        <h2 className="hazard-name">{hazard}</h2>
      </div>

      <div className="metrics-grid">
        <div className="metric-card direction-card">
          <div className="metric-icon">{directionIcon}</div>
          <div className="metric-content">
            <span className="metric-label">Direction</span>
            <span className="metric-value">{direction}</span>
          </div>
        </div>

        <div className="metric-card distance-card">
          <div className="metric-icon">📏</div>
          <div className="metric-content">
            <span className="metric-label">Distance</span>
            <span className="metric-value">{distance.toFixed(1)}m</span>
          </div>
        </div>

        <div className="metric-card confidence-card">
          <div className="metric-icon">🎯</div>
          <div className="metric-content">
            <span className="metric-label">Confidence</span>
            <span className="metric-value">{(confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {guidance && (
        <div className="guidance-box">
          <span className="guidance-icon">💡</span>
          <span className="guidance-text">{guidance}</span>
        </div>
      )}

      {total_hazards > 1 && (
        <div className="additional-hazards">
          <span className="hazard-count">+{total_hazards - 1}</span>
          <span className="hazard-text">more object{total_hazards > 2 ? 's' : ''} nearby</span>
        </div>
      )}
    </div>
  )
}

export default HazardAlert
