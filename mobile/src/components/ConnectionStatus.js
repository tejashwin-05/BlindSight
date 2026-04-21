import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, radius, font } from '../theme';

export default function ConnectionStatus({ isConnected, serverIP, phase }) {
  return (
    <View style={styles.row}>
      <View style={[styles.dot, { backgroundColor: isConnected ? colors.success : colors.critical }]} />
      <Text style={styles.text} numberOfLines={1}>
        {isConnected ? serverIP : 'Disconnected'}
      </Text>
      <View style={styles.phaseBadge}>
        <Text style={styles.phaseText}>Phase {phase}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    marginBottom: spacing.md,
    gap: spacing.sm,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  text: {
    flex: 1,
    color: colors.textSecondary,
    fontSize: font.sm,
  },
  phaseBadge: {
    backgroundColor: colors.primaryDark,
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  phaseText: {
    color: colors.textPrimary,
    fontSize: font.xs,
    fontWeight: '700',
  },
});
