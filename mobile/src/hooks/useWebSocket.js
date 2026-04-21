import { useRef, useCallback, useEffect } from 'react';

/**
 * WebSocket hook that mirrors the web frontend's useWebSocket.
 * Handles connect / disconnect / auto-reconnect / message routing.
 */
export default function useWebSocket({ onMessage, onConnect, onDisconnect, onError }) {
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const shouldReconnect = useRef(false);
  const urlRef = useRef('');

  const clearReconnect = () => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
  };

  const connect = useCallback((ip) => {
    // Accept bare IP:PORT or full ws:// URL
    const url = ip.startsWith('ws://') || ip.startsWith('wss://')
      ? ip
      : `ws://${ip}`;

    urlRef.current = url;
    shouldReconnect.current = true;

    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        clearReconnect();
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch (e) {
          console.warn('[WS] Failed to parse message:', e);
        }
      };

      ws.onclose = () => {
        onDisconnect?.();
        if (shouldReconnect.current) {
          reconnectTimer.current = setTimeout(() => {
            connect(urlRef.current);
          }, 3000);
        }
      };

      ws.onerror = (e) => {
        onError?.(e);
      };
    } catch (e) {
      onError?.(e);
    }
  }, [onMessage, onConnect, onDisconnect, onError]);

  const disconnect = useCallback(() => {
    shouldReconnect.current = false;
    clearReconnect();
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const sendMessage = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      shouldReconnect.current = false;
      clearReconnect();
      wsRef.current?.close();
    };
  }, []);

  return { connect, disconnect, sendMessage };
}
