import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = `ws://${window.location.hostname}:8765`;
const BlindSightContext = createContext(null);

export function BlindSightProvider({ children }) {
  const wsRef          = useRef(null);
  const reconnectTimer = useRef(null);
  const pingTimer      = useRef(null);
  // Stable ref to latest message handler — avoids stale closures on the WS
  const onMessageRef   = useRef(null);

  const hazardClearTimer = useRef(null);

  const [wsStatus,         setWsStatus]        = useState('disconnected');
  const [hazard,           setHazard]           = useState(null);
  const [alertLog,         setAlertLog]         = useState([]);
  const [frameData,        setFrameData]        = useState(null);  // base64 JPEG from server
  const [heatmap,          setHeatmap]          = useState({ left: 'safe', centerL: 'safe', centerR: 'safe', right: 'safe' });
  const [sceneDescription, setSceneDescription] = useState('');
  const [sceneLoading,     setSceneLoading]     = useState(false);
  const [mcpResult,        setMcpResult]        = useState(null);
  const [mcpLoading,       setMcpLoading]       = useState(false);
  const [speaking,         setSpeaking]         = useState(false);
  const [activeTool,       setActiveTool]       = useState('navigate');
  const [settings,         setSettings]         = useState({
    hazardAlerts:     true,
    voiceTTS:         true,
    florence2:        true,
    heatmapOverlay:   true,
    debounceInterval: 5,
    cameraIndex:      0,
    guardianPhone:    '+91 98765 43210',
    guardianTimeout:  60,
  });

  // Keep a ref to settings so handlers always read the latest value
  const settingsRef = useRef(settings);
  useEffect(() => { settingsRef.current = settings; }, [settings]);

  // ── TTS ──────────────────────────────────────────────────────
  const speak = useCallback((text) => {
    if (!text || !settingsRef.current.voiceTTS) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate  = 0.95;
    utt.pitch = 1;
    utt.onstart = () => setSpeaking(true);
    utt.onend   = () => setSpeaking(false);
    utt.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utt);
  }, []);

  const addAlert = useCallback((text, type = 'warn') => {
    const ts = new Date().toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
    setAlertLog(prev => [{ text, type, ts, id: Date.now() }, ...prev].slice(0, 50));
  }, []);

  // ── Message handler (kept in ref so WS always calls latest) ──
  // The WebSocket does: ws.onmessage = (e) => onMessageRef.current(e)
  // so we never need to re-assign ws.onmessage when deps change.
  useEffect(() => {
    onMessageRef.current = (event) => {
      let data;
      try { data = JSON.parse(event.data); }
      catch { return; }

      // ── frame ────────────────────────────────────────────────
      if (data.type === 'frame') {
        setFrameData(data.data);
      }

      // ── phase_1 ─────────────────────────────────────────────
      if (data.type === 'phase_1') {
        if (data.hazard) {
          // Cancel any pending clear — a new hazard just arrived
          clearTimeout(hazardClearTimer.current);
          setHazard({
            label:      data.hazard,
            direction:  data.direction,
            distance:   data.distance,
            guidance:   data.guidance,
            confidence: data.confidence,
          });

          // Derive heatmap from direction + distance
          const lanes = { left: 'safe', centerL: 'safe', centerR: 'safe', right: 'safe' };
          const dir  = (data.direction || '').toLowerCase();
          const dist = typeof data.distance === 'number' ? data.distance : 99;
          const sev  = dist <= 1.5 ? 'blocked' : dist <= 3.0 ? 'caution' : 'safe';
          if (dir === 'left')   { lanes.left    = sev; lanes.centerL = dist <= 2.5 ? 'caution' : 'safe'; }
          if (dir === 'center') { lanes.centerL = sev; lanes.centerR = sev; }
          if (dir === 'right')  { lanes.right   = sev; lanes.centerR = dist <= 2.5 ? 'caution' : 'safe'; }
          setHeatmap(lanes);

          if (settingsRef.current.hazardAlerts) {
            const distStr = dist !== 99 ? dist.toFixed(1) : '?';
            addAlert(
              `${data.hazard} · ${data.direction} · ${distStr}m${data.guidance ? ' — ' + data.guidance : ''}`,
              'warn'
            );
            speak(data.guidance || `Hazard: ${data.hazard} on your ${data.direction}, ${distStr} meters`);
          }
        } else {
          // null hazard = path clear — hold current display for 2s before clearing
          clearTimeout(hazardClearTimer.current);
          hazardClearTimer.current = setTimeout(() => {
            setHazard(null);
            setHeatmap({ left: 'safe', centerL: 'safe', centerR: 'safe', right: 'safe' });
            if (data.total_hazards === 0) {
              setAlertLog(prev => {
                if (prev[0]?.type === 'clear') return prev; // don't spam
                const ts = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                return [{ text: 'Path clear — no obstacles detected', type: 'clear', ts, id: Date.now() }, ...prev].slice(0, 50);
              });
            }
          }, 2000);
        }
      }

      // ── phase_2 ─────────────────────────────────────────────
      if (data.type === 'phase_2') {
        if (data.status === 'processing') {
          setSceneLoading(true);
          setSceneDescription('');
        }
        if (data.status === 'done') {
          setSceneLoading(false);
          setSceneDescription(data.description || '');
          if (data.description) {
            addAlert('Scene described', 'safe');
            speak(data.description);
          }
        }
      }

      // ── mcp_response ─────────────────────────────────────────
      if (data.type === 'mcp_response') {
        setMcpLoading(false);
        setMcpResult(data.result ?? data);
        const summary = data.spoken_summary || data.result?.spoken_summary;
        if (summary) {
          addAlert(`Assistant: ${data.tool} complete`, 'safe');
          speak(summary);
        }
      }

      // pong — no action needed
    };
  }); // no deps — runs every render so ref always has latest closures

  // ── WebSocket connect ─────────────────────────────────────────
  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState < 2) return;
    setWsStatus('connecting');

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('connected');
      addAlert('Connected to BlindSight server', 'safe');
      clearInterval(pingTimer.current);
      pingTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 10000);
    };

    // Delegate to the always-current ref
    ws.onmessage = (e) => onMessageRef.current && onMessageRef.current(e);

    ws.onclose = () => {
      setWsStatus('disconnected');
      setHazard(null);
      clearInterval(pingTimer.current);
      addAlert('Disconnected — reconnecting in 3s…', 'warn');
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, [addAlert]); // stable — addAlert never changes

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      clearInterval(pingTimer.current);
      wsRef.current?.close();
    };
  }, []); // eslint-disable-line

  // ── Public actions ────────────────────────────────────────────
  const requestScene = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setSceneLoading(true);
      setSceneDescription('');
      wsRef.current.send(JSON.stringify({ type: 'trigger_phase2' }));
    } else {
      addAlert('Not connected — cannot request scene description', 'warn');
    }
  }, [addAlert]);

  const callMCPTool = useCallback((tool, query) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      setMcpResult({ error: 'Not connected to server. Check Settings.' });
      return;
    }
    setMcpLoading(true);
    setMcpResult(null);
    wsRef.current.send(JSON.stringify({ type: 'mcp_request', tool, input: query }));
    addAlert(`Assistant: sending ${tool} request…`, 'safe');
  }, [addAlert]);

  const sendWS = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  const updateSetting = useCallback((key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  }, []);

  return (
    <BlindSightContext.Provider value={{
      wsStatus, hazard, alertLog, heatmap, frameData,
      sceneDescription, sceneLoading, requestScene,
      mcpResult, mcpLoading, callMCPTool,
      speaking, activeTool, setActiveTool,
      settings, updateSetting, sendWS,
      clearAlerts: () => setAlertLog([]),
    }}>
      {children}
    </BlindSightContext.Provider>
  );
}

export const useBlindSight = () => useContext(BlindSightContext);
