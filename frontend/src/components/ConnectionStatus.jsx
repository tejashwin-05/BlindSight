import './ConnectionStatus.css'

function ConnectionStatus({ isConnected, serverIP, phase }) {
  return (
    <div className="connection-status">
      <div className="status-card">
        <div className="status-indicator">
          <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="dot-pulse"></span>
          </span>
          <div className="status-info">
            <span className="status-label">Server Status</span>
            <span className="status-value">
              {isConnected ? `Connected to ${serverIP}` : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>
      
      <div className="phase-card">
        <span className="phase-icon">{phase === 1 ? '⚡' : '🔍'}</span>
        <div className="phase-info">
          <span className="phase-label">Active Mode</span>
          <span className={`phase-badge phase-${phase}`}>
            Phase {phase}
          </span>
          <span className="phase-description">
            {phase === 1 ? 'Real-time Detection' : 'Scene Analysis'}
          </span>
        </div>
      </div>
    </div>
  )
}

export default ConnectionStatus
