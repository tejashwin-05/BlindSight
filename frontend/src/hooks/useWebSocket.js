import { useRef, useCallback, useState } from 'react'

function useWebSocket({ onMessage, onConnect, onDisconnect, onError }) {
  const wsRef = useRef(null)
  const [connectionState, setConnectionState] = useState('disconnected')

  const connect = useCallback((serverIP) => {
    console.log('[WebSocket] Attempting to connect to:', serverIP)
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Already connected')
      return
    }

    const wsUrl = serverIP.startsWith('ws://') 
      ? serverIP 
      : `ws://${serverIP}`
    
    console.log('[WebSocket] Connecting to URL:', wsUrl)

    try {
      const ws = new WebSocket(wsUrl)
      console.log('[WebSocket] WebSocket object created, waiting for connection...')
      
      ws.onopen = () => {
        console.log('[WebSocket] ✓ Connected successfully!')
        setConnectionState('connected')
        onConnect?.()
      }

      ws.onmessage = (event) => {
        console.log('[WebSocket] Message received:', event.data)
        try {
          const data = JSON.parse(event.data)
          onMessage?.(data)
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('[WebSocket] ✗ Connection error:', error)
        setConnectionState('error')
        onError?.(error)
      }

      ws.onclose = (event) => {
        console.log('[WebSocket] Connection closed. Code:', event.code, 'Reason:', event.reason)
        setConnectionState('disconnected')
        onDisconnect?.()
      }

      wsRef.current = ws
    } catch (error) {
      console.error('[WebSocket] ✗ Failed to create WebSocket:', error)
      setConnectionState('error')
      onError?.(error)
    }
  }, [onMessage, onConnect, onDisconnect, onError])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  return {
    connect,
    disconnect,
    sendMessage,
    connectionState
  }
}

export default useWebSocket
