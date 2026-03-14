import React, { useState } from 'react';
import { useBlindSight } from '../context/BlindSightContext';
import './SettingsScreen.css';

function Toggle({ on, onChange }) {
  return (
    <button className={`toggle ${on ? 'on' : 'off'}`} onClick={() => onChange(!on)} role="switch" aria-checked={on}>
      <span className="toggle-thumb" />
    </button>
  );
}

function SettingRow({ label, sub, right }) {
  return (
    <div className="setting-row">
      <div className="setting-left">
        <div className="setting-label">{label}</div>
        {sub && <div className="setting-sub">{sub}</div>}
      </div>
      <div className="setting-right">{right}</div>
    </div>
  );
}

function SettingsGroup({ title, children }) {
  return (
    <div className="settings-block">
      {title && <div className="group-title">{title}</div>}
      <div className="settings-group">{children}</div>
    </div>
  );
}

export default function SettingsScreen() {
  const { settings, updateSetting, wsStatus, sendWS } = useBlindSight();
  const [editingGuardian, setEditingGuardian] = useState(false);
  const [guardianDraft, setGuardianDraft] = useState(settings.guardianPhone);

  const saveGuardian = () => {
    updateSetting('guardianPhone', guardianDraft);
    setEditingGuardian(false);
  };

  return (
    <div className="settings-screen">
      <div className="settings-header">
        <span className="settings-section-label">CONFIGURATION</span>
      </div>

      <div className={`connection-card ${wsStatus}`}>
        <div className="conn-left">
          <span className={`conn-dot ${wsStatus}`} />
          <div>
            <div className="conn-title">Backend Connection</div>
            <div className="conn-sub">
              {wsStatus === 'connected'   ? 'WebSocket connected — ws://localhost:8765'
               : wsStatus === 'connecting' ? 'Connecting to ws://localhost:8765…'
               : 'Disconnected — retrying…'}
            </div>
          </div>
        </div>
        <div className="conn-badge">{wsStatus.toUpperCase()}</div>
      </div>

      <SettingsGroup title="Detection">
        <SettingRow label="Hazard alerts"          sub="YOLOv8 real-time detection"      right={<Toggle on={settings.hazardAlerts}    onChange={v => updateSetting('hazardAlerts', v)} />} />
        <SettingRow label="Voice TTS alerts"       sub="Speak hazard guidance aloud"     right={<Toggle on={settings.voiceTTS}        onChange={v => updateSetting('voiceTTS', v)} />} />
        <SettingRow label="Florence-2 scene model" sub="On-demand scene description"     right={<Toggle on={settings.florence2}       onChange={v => updateSetting('florence2', v)} />} />
        <SettingRow label="Heatmap overlay"        sub="Free-space lane visualisation"   right={<Toggle on={settings.heatmapOverlay}  onChange={v => updateSetting('heatmapOverlay', v)} />} />
      </SettingsGroup>

      <SettingsGroup title="Tuning">
        <SettingRow
          label="Debounce interval" sub="Min seconds between same-hazard alerts"
          right={
            <div className="stepper">
              <button onClick={() => updateSetting('debounceInterval', Math.max(1, settings.debounceInterval - 1))}>−</button>
              <span>{settings.debounceInterval}s</span>
              <button onClick={() => updateSetting('debounceInterval', Math.min(30, settings.debounceInterval + 1))}>+</button>
            </div>
          }
        />
        <SettingRow
          label="Camera index" sub="Switch if multiple cameras connected"
          right={
            <div className="stepper">
              <button onClick={() => updateSetting('cameraIndex', Math.max(0, settings.cameraIndex - 1))}>−</button>
              <span>CAM {settings.cameraIndex}</span>
              <button onClick={() => updateSetting('cameraIndex', settings.cameraIndex + 1)}>+</button>
            </div>
          }
        />
      </SettingsGroup>

      <SettingsGroup title="MCP Assistant">
        <SettingRow label="MCP server" sub="http://localhost:8100 — nav, weather, news" right={<span className="val-badge cyan">ACTIVE</span>} />
      </SettingsGroup>

      <div className="guardian-card">
        <div className="guardian-header">
          <span className="guardian-title">GUARDIAN ALERT</span>
          <span className="guardian-badge">SMS + GPS</span>
        </div>
        <div className="guardian-body">
          {editingGuardian ? (
            <div className="guardian-edit">
              <input
                className="guardian-input"
                value={guardianDraft}
                onChange={e => setGuardianDraft(e.target.value)}
                placeholder="+91 XXXXX XXXXX"
                type="tel"
              />
              <div className="guardian-edit-btns">
                <button className="g-save" onClick={saveGuardian}>Save</button>
                <button className="g-cancel" onClick={() => setEditingGuardian(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <div className="guardian-info-row">
              <div>
                <div className="guardian-contact">{settings.guardianPhone}</div>
                <div className="guardian-sub">SMS + GPS sent if disconnected for &gt;{settings.guardianTimeout}s</div>
              </div>
              <button className="g-edit-btn" onClick={() => setEditingGuardian(true)}>Edit</button>
            </div>
          )}
        </div>
        <SettingRow
          label="Timeout before alert" sub="Seconds until SMS triggers"
          right={
            <div className="stepper">
              <button onClick={() => updateSetting('guardianTimeout', Math.max(10, settings.guardianTimeout - 10))}>−</button>
              <span>{settings.guardianTimeout}s</span>
              <button onClick={() => updateSetting('guardianTimeout', settings.guardianTimeout + 10)}>+</button>
            </div>
          }
        />
      </div>

      <div className="settings-block">
        <div className="group-title">Calibration</div>
        <div className="settings-group">
          <div className="calib-row">
            <div>
              <div className="setting-label">Distance calibration</div>
              <div className="setting-sub">Place a known object exactly 1 metre from camera, then run</div>
            </div>
            <button className="calib-btn" onClick={() => { sendWS({ action: 'calibrate' }); alert('Calibration started — place object 1m from camera.'); }}>
              Run
            </button>
          </div>
        </div>
      </div>

      <div className="about-block">
        <span className="about-name">BlindSight</span>
        <span className="about-ver">v1.0 · YOLOv8 · Florence-2 · WebSocket</span>
      </div>
    </div>
  );
}
