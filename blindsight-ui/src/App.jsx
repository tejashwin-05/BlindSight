import React, { useState } from 'react';
import { BlindSightProvider } from './context/BlindSightContext';
import StatusBar from './components/StatusBar';
import BottomNav from './components/BottomNav';
import RadarScreen from './screens/RadarScreen';
import AssistantScreen from './screens/AssistantScreen';
import SettingsScreen from './screens/SettingsScreen';
import './App.css';

function AppShell() {
  const [activeTab, setActiveTab] = useState('radar');

  return (
    <div className="app-shell">
      <StatusBar />
      <main className="app-main">
        <div className={`screen-slot ${activeTab === 'radar' ? 'visible' : ''}`}>
          <RadarScreen onNavigateTo={setActiveTab} />
        </div>
        <div className={`screen-slot ${activeTab === 'assistant' ? 'visible' : ''}`}>
          <AssistantScreen />
        </div>
        <div className={`screen-slot ${activeTab === 'settings' ? 'visible' : ''}`}>
          <SettingsScreen />
        </div>
      </main>
      <BottomNav activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}

export default function App() {
  return (
    <BlindSightProvider>
      <AppShell />
    </BlindSightProvider>
  );
}
