import { useState, useEffect, useRef } from 'react'
import './App.css'
import HazardAlert from './components/HazardAlert'
import SceneDescription from './components/SceneDescription'
import ConnectionStatus from './components/ConnectionStatus'
import ControlPanel from './components/ControlPanel'
import AssistantPanel from './components/AssistantPanel'
import FeatureDialog from './components/FeatureDialog'
import MCPNotification from './components/MCPNotification'
import useWebSocket from './hooks/useWebSocket'
import useSpeech from './hooks/useSpeech'

function App() {
  const [serverIP, setServerIP] = useState(localStorage.getItem('serverIP') || '')
  const [isConnected, setIsConnected] = useState(false)
  const [hazardData, setHazardData] = useState(null)
  const [sceneData, setSceneData] = useState(null)
  const [phase, setPhase] = useState(1)
  const [connectionError, setConnectionError] = useState('')
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [activeFeature, setActiveFeature] = useState(null)
  const [mcpNotification, setMcpNotification] = useState(null)
  
  const { connect, disconnect, sendMessage, connectionState } = useWebSocket({
    onMessage: handleMessage,
    onConnect: () => {
      setIsConnected(true)
      setConnectionError('')
    },
    onDisconnect: () => {
      setIsConnected(false)
      setConnectionError('Connection lost')
    },
    onError: (error) => {
      setConnectionError('Failed to connect. Make sure the server is running.')
    }
  })
  
  const { speak, stopSpeaking } = useSpeech()

  function handleMessage(data) {
    console.log('[App] Received message:', data)
    
    if (data.type === 'phase_1') {
      setHazardData(data)
      setPhase(1)
      
      // Speak hazard alerts using the same format as server
      if (data.hazard && data.distance && data.direction) {
        let message = ''
        
        // Use the same threshold as server (NEAR_HAZARD_DISTANCE_M = 1.5)
        if (data.distance <= 1.5) {
          message = `Hazard near: ${data.hazard} on your ${data.direction}, ${data.distance.toFixed(1)} meters`
        } else {
          message = `Next object: ${data.hazard} on your ${data.direction}, ${data.distance.toFixed(1)} meters`
        }
        
        // Add guidance if available
        if (data.guidance) {
          message = `${message}. ${data.guidance}.`
        }
        
        console.log('[Speech] Speaking:', message)
        speak(message)
      }
    } else if (data.type === 'phase_2') {
      setSceneData(data)
      setPhase(2)
      
      if (data.status === 'done' && data.description) {
        console.log('[Speech] Speaking scene description')
        speak(data.description)
      }
    } else if (data.type === 'mcp_response') {
      // Handle MCP tool responses
      console.log('[MCP] Response received:', data)
      if (data.spoken_summary) {
        speak(data.spoken_summary)
      }
      // You could also display the response in a notification or modal
    } else if (data.type === 'mcp_response') {
      // Handle MCP tool responses
      console.log('[MCP] Response received:', data)
      setMcpNotification(data)
      if (data.spoken_summary) {
        speak(data.spoken_summary)
      }
    } else if (data.type === 'pong') {
      // Just a heartbeat response, no action needed
      console.log('[App] Pong received')
    }
  }

  function handleConnect() {
    if (serverIP) {
      localStorage.setItem('serverIP', serverIP)
      connect(serverIP)
    }
  }

  function handleDisconnect() {
    disconnect()
    setHazardData(null)
    setSceneData(null)
  }

  function triggerPhase2() {
    sendMessage({ type: 'trigger_phase2' })
    stopSpeaking()
  }

  async function handleFeatureRequest(featureId, input) {
    console.log('[Assistant] Feature requested:', featureId, input)
    
    // Send MCP tool request to server
    sendMessage({
      type: 'mcp_request',
      tool: featureId,
      input: input
    })
    
    setActiveFeature(null)
    speak('Processing your request')
  }

  // Ping server every 5 seconds
  useEffect(() => {
    if (!isConnected) return
    
    const interval = setInterval(() => {
      sendMessage({ type: 'ping' })
    }, 5000)
    
    return () => clearInterval(interval)
  }, [isConnected, sendMessage])

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo-container">
          <span className="logo">👁️</span>
          <h1>BlindSight</h1>
        </div>
        <p>Assistive Navigation System</p>
      </header>

      <main className="app-main">
        {!isConnected ? (
          <div className="connection-panel">
            <h2>Connect to Server</h2>
            <input
              type="text"
              placeholder="Enter server IP (e.g., 192.168.1.100:8765)"
              value={serverIP}
              onChange={(e) => setServerIP(e.target.value)}
              className="ip-input"
            />
            <button onClick={handleConnect} className="btn btn-primary">
              Connect
            </button>
            {connectionError && (
              <div className="error-message">{connectionError}</div>
            )}
          </div>
        ) : (
          <>
            <ConnectionStatus 
              isConnected={isConnected} 
              serverIP={serverIP}
              phase={phase}
            />
            
            <div className="content-area">
              {phase === 1 && hazardData && (
                <HazardAlert data={hazardData} />
              )}
              
              {phase === 2 && sceneData && (
                <SceneDescription data={sceneData} />
              )}
            </div>

            <ControlPanel
              onTriggerPhase2={triggerPhase2}
              onDisconnect={handleDisconnect}
              onOpenAssistant={() => setAssistantOpen(true)}
              isProcessing={sceneData?.status === 'processing'}
            />

            <AssistantPanel
              isOpen={assistantOpen}
              onClose={() => setAssistantOpen(false)}
              onFeatureRequest={(featureId) => setActiveFeature(featureId)}
            />

            <FeatureDialog
              feature={activeFeature}
              onSubmit={handleFeatureRequest}
              onClose={() => setActiveFeature(null)}
            />

            <MCPNotification
              notification={mcpNotification}
              onClose={() => setMcpNotification(null)}
            />
          </>
        )}
      </main>
    </div>
  )
}

export default App
