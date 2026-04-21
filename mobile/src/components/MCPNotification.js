import React, { useEffect } from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Animated, Platform } from 'react-native';
import { colors, spacing, radius, font } from '../theme';

export default function MCPNotification({ notification, onClose }) {
  const opacity = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (notification) {
      Animated.timing(opacity, { toValue: 1, duration: 250, useNativeDriver: true }).start();
    } else {
      opacity.setValue(0);
    }
  }, [notification]);

  if (!notification) return null;

  const toolLabel = notification.tool?.replace(/_/g, ' ') ?? 'Result';

  return (
    <Animated.View style={[styles.card, { opacity }]}>
      <View style={styles.header}>
        <Text style={styles.toolName}>{toolLabel.toUpperCase()}</Text>
        <TouchableOpacity onPress={onClose} accessibilityLabel="Dismiss notification">
          <Text style={styles.close}>✕</Text>
        </TouchableOpacity>
      </View>

      {notification.spoken_summary && (
        <Text style={styles.summary}>{notification.spoken_summary}</Text>
      )}

      {notification.result && typeof notification.result === 'object' && (
        <ScrollView style={styles.resultScroll} nestedScrollEnabled>
          <Text style={styles.resultText}>
            {JSON.stringify(notification.result, null, 2)}
          </Text>
        </ScrollView>
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  toolName: {
    color: colors.primary,
    fontSize: font.xs,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  close: {
    color: colors.textMuted,
    fontSize: font.md,
    padding: spacing.xs,
  },
  summary: {
    color: colors.textPrimary,
    fontSize: font.md,
    lineHeight: 22,
    marginBottom: spacing.sm,
  },
  resultScroll: {
    maxHeight: 160,
    backgroundColor: colors.surface,
    borderRadius: radius.sm,
    padding: spacing.sm,
  },
  resultText: {
    color: colors.textMuted,
    fontSize: font.xs,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
});
