import React, { useState, useEffect } from 'react';
import { useBlindSight } from '../context/BlindSightContext';
import './StatusBar.css';

export default function StatusBar() {
  const { wsStatus } = useBlindSight();
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () => {
      setTime(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }));
    };
    tick();
    const id = setInterval(tick, 10000);
    return () => clearInterval(id);
  }, []);

  const statusLabel = wsStatus === 'connected' ? 'LIVE'
    : wsStatus === 'connecting' ? 'LINKING' : 'OFFLINE';
  const statusClass = wsStatus === 'connected' ? 'connected'
    : wsStatus === 'connecting' ? 'connecting' : 'disconnected';

  return (
    <div className="status-bar">
      <div className={`status-pill ${statusClass}`}>
        <span className="status-dot" />
        {statusLabel}
      </div>
      <span className="status-time">{time}</span>
      <div className="status-right">
        <span className="status-label">BLINDSIGHT</span>
      </div>
    </div>
  );
}
