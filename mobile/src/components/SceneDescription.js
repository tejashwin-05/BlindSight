import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors, spacing, radius, font } from '../theme';

export default function SceneDescription({ data }) {
  if (!data) return null;

  const isProcessing = data.status === 'processing';

  return (
    <View style={styles.card}>
      <Text style={styles.label}>🔍 SCENE DESCRIPTION</Text>

      {isProcessing ? (
        <View style={styles.processingRow}>
          <ActivityIndicator color={colors.primary} size="small" />
          <Text style={styles.processingText}>Analyzing scene...</Text>
        </View>
      ) : (
        <Text style={styles.description}>{data.description}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  label: {
    fontSize: font.xs,
    fontWeight: '700',
    color: colors.primary,
    letterSpacing: 1.5,
    marginBottom: spacing.sm,
  },
  processingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  processingText: {
    color: colors.textSecondary,
    fontSize: font.md,
  },
  description: {
    color: colors.textPrimary,
    fontSize: font.md,
    lineHeight: 24,
  },
});
