import React, { useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import ConnectScreen from './src/screens/ConnectScreen';
import MainScreen from './src/screens/MainScreen';

export default function App() {
  const [serverIP, setServerIP] = useState(null);
  const [connectionError, setConnectionError] = useState('');

  const handleConnect = (ip) => {
    setConnectionError('');
    setServerIP(ip);
  };

  const handleDisconnect = () => {
    setServerIP(null);
  };

  return (
    <>
      <StatusBar style="light" backgroundColor="#0a0a1a" />
      {serverIP ? (
        <MainScreen
          serverIP={serverIP}
          onDisconnect={handleDisconnect}
        />
      ) : (
        <ConnectScreen
          onConnect={handleConnect}
          error={connectionError}
        />
      )}
    </>
  );
}
