import React, { useState, useEffect, useCallback } from 'react';
import {
  View, ScrollView, StyleSheet, SafeAreaView, Text, TouchableOpacity,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import * as Location from 'expo-location';

import ConnectionStatus from '../components/ConnectionStatus';
import HazardAlert from '../components/HazardAlert';
import SceneDescription from '../components/SceneDescription';
import ControlPanel from '../components/ControlPanel';
import AssistantPanel from '../components/AssistantPanel';
import FeatureDialog from '../components/FeatureDialog';
import MCPNotification from '../components/MCPNotification';

import useWebSocket from '../hooks/useWebSocket';
import useSpeech from '../hooks/useSpeech';
import { colors, spacing, font } from '../theme';

export default function MainScreen({ serverIP, onDisconnect }) {
  const [isConnected, setIsConnected] = useState(false);
  const [hazardData, setHazardData] = useState(null);
  const [sceneData, setSceneData] = useState(null);
  const [phase, setPhase] = useState(1);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [activeFeature, setActiveFeature] = useState(null);
  const [mcpNotification, setMcpNotification] = useState(null);
  const [locationGranted, setLocationGranted] = useState(false);

  const { speak, stopSpeaking } = useSpeech();

  // ── Message handler ──────────────────────────────────────────
  const handleMessage = useCallback((data) => {
    if (data.type === 'phase_1') {
      setHazardData(data);
      setPhase(1);

      if (data.hazard && data.distance != null && data.direction) {
        const prefix = data.distance <= 1.5 ? 'Hazard near' : 'Next object';
        let msg = `${prefix}: ${data.hazard} on your ${data.direction}, ${data.distance.toFixed(1)} meters`;
        if (data.guidance) msg += `. ${data.guidance}.`;
        speak(msg);
        Haptics.impactAsync(
          data.distance <= 1.5
            ? Haptics.ImpactFeedbackStyle.Heavy
            : Haptics.ImpactFeedbackStyle.Light
        );
      }
    } else if (data.type === 'phase_2') {
      setSceneData(data);
      setPhase(2);
      if (data.status === 'done' && data.description) {
        speak(data.description);
      }
    } else if (data.type === 'mcp_response') {
      setMcpNotification(data);
      if (data.spoken_summary) speak(data.spoken_summary);
    }
    // pong — no action needed
  }, [speak]);

  const { connect, disconnect, sendMessage } = useWebSocket({
    onMessage: handleMessage,
    onConnect: () => {
      setIsConnected(true);
      speak('Connected to BlindSight server');
    },
    onDisconnect: () => {
      setIsConnected(false);
    },
    onError: () => {
      setIsConnected(false);
    },
  });

  // ── Connect on mount ─────────────────────────────────────────
  useEffect(() => {
    connect(serverIP);
    return () => disconnect();
  }, [serverIP]);

  // ── Heartbeat ping with GPS ──────────────────────────────────
  useEffect(() => {
    if (!isConnected) return;

    let locationSub = null;

    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        setLocationGranted(true);
        locationSub = await Location.watchPositionAsync(
          { accuracy: Location.Accuracy.Balanced, timeInterval: 10000, distanceInterval: 10 },
          (loc) => {
            sendMessage({
              type: 'location_update',
              latitude: loc.coords.latitude,
              longitude: loc.coords.longitude,
            });
          }
        );
      }
    })();

    const pingInterval = setInterval(() => {
      sendMessage({ type: 'ping' });
    }, 5000);

    return () => {
      clearInterval(pingInterval);
      locationSub?.remove();
    };
  }, [isConnected, sendMessage]);

  // ── Actions ──────────────────────────────────────────────────
  const triggerPhase2 = () => {
    sendMessage({ type: 'trigger_phase2' });
    stopSpeaking();
    setSceneData({ status: 'processing' });
    setPhase(2);
  };

  const handleDisconnect = () => {
    disconnect();
    onDisconnect();
  };

  const handleFeatureRequest = (featureId, input) => {
    sendMessage({ type: 'mcp_request', tool: featureId, input });
    speak('Processing your request');
    setActiveFeature(null);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.logo}>👁️ BlindSight</Text>
        {!locationGranted && (
          <Text style={styles.locationWarning}>📍 Location off</Text>
        )}
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <ConnectionStatus isConnected={isConnected} serverIP={serverIP} phase={phase} />

        {phase === 1 && hazardData && <HazardAlert data={hazardData} />}
        {phase === 2 && sceneData && <SceneDescription data={sceneData} />}

        {mcpNotification && (
          <MCPNotification
            notification={mcpNotification}
            onClose={() => setMcpNotification(null)}
          />
        )}

        {/* Switch back to Phase 1 view */}
        {phase === 2 && (
          <TouchableOpacity
            style={styles.backBtn}
            onPress={() => { setPhase(1); setSceneData(null); }}
            accessibilityLabel="Back to hazard detection"
          >
            <Text style={styles.backBtnText}>← Back to Hazard Detection</Text>
          </TouchableOpacity>
        )}
      </ScrollView>

      <View style={styles.footer}>
        <ControlPanel
          onTriggerPhase2={triggerPhase2}
          onDisconnect={handleDisconnect}
          onOpenAssistant={() => setAssistantOpen(true)}
          isProcessing={sceneData?.status === 'processing'}
        />
      </View>

      <AssistantPanel
        isOpen={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        onFeatureSelect={(feature) => {
          setAssistantOpen(false);
          setActiveFeature(feature);
        }}
      />

      <FeatureDialog
        feature={activeFeature}
        onSubmit={handleFeatureRequest}
        onClose={() => setActiveFeature(null)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  logo: {
    color: colors.textPrimary,
    fontSize: font.lg,
    fontWeight: '800',
    letterSpacing: 1,
  },
  locationWarning: {
    color: colors.warning,
    fontSize: font.xs,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing.lg,
    paddingBottom: spacing.md,
  },
  footer: {
    padding: spacing.lg,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  backBtn: {
    alignSelf: 'flex-start',
    marginTop: spacing.sm,
  },
  backBtnText: {
    color: colors.primary,
    fontSize: font.sm,
  },
});
