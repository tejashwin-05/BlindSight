import React, { useState, useEffect } from 'react';
import {
  Modal, View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors, spacing, radius, font } from '../theme';

export default function FeatureDialog({ feature, onSubmit, onClose }) {
  const [input, setInput] = useState('');

  useEffect(() => {
    if (feature) setInput('');
  }, [feature]);

  if (!feature) return null;

  const handleSubmit = () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    onSubmit(feature.id, input.trim());
    onClose();
  };

  return (
    <Modal visible={!!feature} animationType="fade" transparent onRequestClose={onClose}>
      <KeyboardAvoidingView
        style={styles.overlay}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View style={styles.dialog}>
          <Text style={styles.title}>{feature.label}</Text>

          {feature.hasInput ? (
            <>
              <TextInput
                style={styles.input}
                placeholder={feature.placeholder}
                placeholderTextColor={colors.textMuted}
                value={input}
                onChangeText={setInput}
                autoFocus
                returnKeyType="send"
                onSubmitEditing={handleSubmit}
                accessibilityLabel={feature.placeholder}
              />
              <View style={styles.row}>
                <TouchableOpacity style={[styles.btn, styles.btnCancel]} onPress={onClose}>
                  <Text style={styles.btnText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.btn, styles.btnSubmit, !input.trim() && styles.btnDisabled]}
                  onPress={handleSubmit}
                  disabled={!input.trim()}
                >
                  <Text style={styles.btnText}>Send</Text>
                </TouchableOpacity>
              </View>
            </>
          ) : (
            <View style={styles.row}>
              <TouchableOpacity style={[styles.btn, styles.btnCancel]} onPress={onClose}>
                <Text style={styles.btnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, styles.btnSubmit]} onPress={handleSubmit}>
                <Text style={styles.btnText}>Get Info</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  dialog: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: {
    color: colors.textPrimary,
    fontSize: font.lg,
    fontWeight: '700',
    marginBottom: spacing.md,
  },
  input: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    color: colors.textPrimary,
    fontSize: font.md,
    marginBottom: spacing.md,
  },
  row: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  btn: {
    flex: 1,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  btnCancel: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
  },
  btnSubmit: {
    backgroundColor: colors.primary,
  },
  btnDisabled: {
    opacity: 0.4,
  },
  btnText: {
    color: colors.textPrimary,
    fontSize: font.md,
    fontWeight: '600',
  },
});
