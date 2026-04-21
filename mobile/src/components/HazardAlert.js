import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, radius, font } from '../theme';

const DIRECTION_ARROW = { left: '←', center: '↑', right: '→' };

function getUrgency(distance) {
  if (!distance) return 'info';
  if (distance <= 1.5) return 'critical';
  if (distance <= 3.0) return 'warning';
  return 'info';
}

const urgencyStyle = {
  critical: { border: colors.critical, bg: colors.criticalBg, label: '⚠ HAZARD NEAR' },
  warning:  { border: colors.warning,  bg: colors.warningBg,  label: '⚡ NEXT OBJECT' },
  info:     { border: colors.info,     bg: colors.infoBg,     label: '👁 DETECTED' },
};

export default function HazardAlert({ data }) {
  if (!data || !data.hazard) return null;

  const urgency = getUrgency(data.distance);
  const { border, bg, label } = urgencyStyle[urgency];
  const arrow = DIRECTION_ARROW[data.direction] || '↑';

  return (
    <View style={[styles.card, { borderColor: border, backgroundColor: bg }]}>
      <Text style={[styles.label, { color: border }]}>{label}</Text>

      <View style={styles.row}>
        <Text style={styles.hazardName}>{data.hazard?.toUpperCase()}</Text>
        <Text style={[styles.arrow, { color: border }]}>{arrow}</Text>
      </View>

      <View style={styles.metaRow}>
        {data.distance != null && (
          <View style={[styles.badge, { borderColor: border }]}>
            <Text style={[styles.badgeText, { color: border }]}>
              {data.distance.toFixed(1)} m
            </Text>
          </View>
        )}
        {data.direction && (
          <View style={[styles.badge, { borderColor: border }]}>
            <Text style={[styles.badgeText, { color: border }]}>
              {data.direction}
            </Text>
          </View>
        )}
        {data.confidence != null && (
          <View style={[styles.badge, { borderColor: colors.border }]}>
            <Text style={[styles.badgeText, { color: colors.textSecondary }]}>
              {Math.round(data.confidence * 100)}%
            </Text>
          </View>
        )}
      </View>

      {data.guidance && (
        <Text style={styles.guidance}>{data.guidance}</Text>
      )}

      {data.total_hazards > 1 && (
        <Text style={styles.muted}>+{data.total_hazards - 1} more hazard(s) in frame</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 2,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
  },
  label: {
    fontSize: font.xs,
    fontWeight: '700',
    letterSpacing: 1.5,
    marginBottom: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  hazardName: {
    fontSize: font.xl,
    fontWeight: '800',
    color: colors.textPrimary,
    flex: 1,
  },
  arrow: {
    fontSize: font.xxl,
    fontWeight: '900',
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  badge: {
    borderWidth: 1,
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  badgeText: {
    fontSize: font.sm,
    fontWeight: '600',
  },
  guidance: {
    fontSize: font.md,
    color: colors.textSecondary,
    fontStyle: 'italic',
    marginTop: spacing.xs,
  },
  muted: {
    fontSize: font.xs,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
});
