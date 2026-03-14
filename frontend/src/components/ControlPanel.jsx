import './ControlPanel.css'

function ControlPanel({ onTriggerPhase2, onDisconnect, onOpenAssistant, isProcessing }) {
  return (
    <div className="control-panel">
      <button 
        className="control-btn assistant-btn"
        onClick={onOpenAssistant}
      >
        <span className="btn-icon">🤖</span>
        <div className="btn-content">
          <span className="btn-text">AI Assistant</span>
          <span className="btn-subtitle">MCP Tools</span>
        </div>
      </button>

      <button 
        className="control-btn scene-btn"
        onClick={onTriggerPhase2}
        disabled={isProcessing}
      >
        <span className="btn-icon">{isProcessing ? '⏳' : '🔍'}</span>
        <div className="btn-content">
          <span className="btn-text">
            {isProcessing ? 'Analyzing...' : 'Describe Scene'}
          </span>
          <span className="btn-subtitle">Phase 2</span>
        </div>
      </button>
      
      <button 
        className="control-btn disconnect-btn"
        onClick={onDisconnect}
      >
        <span className="btn-icon">🔌</span>
        <div className="btn-content">
          <span className="btn-text">Disconnect</span>
        </div>
      </button>
    </div>
  )
}

export default ControlPanel
