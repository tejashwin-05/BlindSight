import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet, ActivityIndicator } from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors, spacing, radius, font } from '../theme';

export default function ControlPanel({ onTriggerPhase2, onDisconnect, onOpenAssistant, isProcessing }) {
  const press = (fn) => () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    fn();
  };

  return (
    <View style={styles.container}>
      {/* Describe Scene — large primary button */}
      <TouchableOpacity
        style={[styles.btn, styles.btnPrimary, isProcessing && styles.btnDisabled]}
        onPress={press(onTriggerPhase2)}
        disabled={isProcessing}
        accessibilityLabel="Describe scene"
        accessibilityRole="button"
      >
        {isProcessing
          ? <ActivityIndicator color={colors.textPrimary} />
          : <Text style={styles.btnText}>🔍  Describe Scene</Text>
        }
      </TouchableOpacity>

      <View style={styles.row}>
        {/* AI Assistant */}
        <TouchableOpacity
          style={[styles.btn, styles.btnSecondary, styles.flex1]}
          onPress={press(onOpenAssistant)}
          accessibilityLabel="Open AI assistant"
          accessibilityRole="button"
        >
          <Text style={styles.btnText}>🤖  Assistant</Text>
        </TouchableOpacity>

        {/* Disconnect */}
        <TouchableOpacity
          style={[styles.btn, styles.btnDanger, styles.flex1]}
          onPress={press(onDisconnect)}
          accessibilityLabel="Disconnect from server"
          accessibilityRole="button"
        >
          <Text style={styles.btnText}>✕  Disconnect</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.sm,
    paddingTop: spacing.md,
  },
  row: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  flex1: { flex: 1 },
  btn: {
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
  },
  btnPrimary: {
    backgroundColor: colors.primary,
  },
  btnSecondary: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
  },
  btnDanger: {
    backgroundColor: 'rgba(255,68,68,0.15)',
    borderWidth: 1,
    borderColor: colors.critical,
  },
  btnDisabled: {
    opacity: 0.5,
  },
  btnText: {
    color: colors.textPrimary,
    fontSize: font.md,
    fontWeight: '600',
  },
});
