import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, SafeAreaView,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { colors, spacing, radius, font } from '../theme';

const STORAGE_KEY = '@blindsight_server_ip';

export default function ConnectScreen({ onConnect, error }) {
  const [ip, setIp] = useState('');

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((saved) => {
      if (saved) setIp(saved);
    });
  }, []);

  const handleConnect = async () => {
    const trimmed = ip.trim();
    if (!trimmed) return;
    await AsyncStorage.setItem(STORAGE_KEY, trimmed);
    onConnect(trimmed);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Logo */}
        <View style={styles.logoArea}>
          <Text style={styles.logoIcon}>👁️</Text>
          <Text style={styles.logoTitle}>BlindSight</Text>
          <Text style={styles.logoSub}>Assistive Navigation System</Text>
        </View>

        {/* Connect card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Connect to Server</Text>
          <Text style={styles.cardHint}>Enter the IP and port of your EcoSight server</Text>

          <TextInput
            style={styles.input}
            placeholder="192.168.1.100:8765"
            placeholderTextColor={colors.textMuted}
            value={ip}
            onChangeText={setIp}
            keyboardType="url"
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="go"
            onSubmitEditing={handleConnect}
            accessibilityLabel="Server IP address"
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity
            style={[styles.btn, !ip.trim() && styles.btnDisabled]}
            onPress={handleConnect}
            disabled={!ip.trim()}
            accessibilityLabel="Connect to server"
            accessibilityRole="button"
          >
            <Text style={styles.btnText}>Connect</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.footer}>
          Make sure the server is running on the same network
        </Text>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: spacing.lg,
  },
  logoArea: {
    alignItems: 'center',
    marginBottom: spacing.xxl,
  },
  logoIcon: {
    fontSize: 64,
    marginBottom: spacing.sm,
  },
  logoTitle: {
    fontSize: font.xxl,
    fontWeight: '900',
    color: colors.textPrimary,
    letterSpacing: 2,
  },
  logoSub: {
    fontSize: font.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
    letterSpacing: 1,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.lg,
  },
  cardTitle: {
    color: colors.textPrimary,
    fontSize: font.lg,
    fontWeight: '700',
    marginBottom: spacing.xs,
  },
  cardHint: {
    color: colors.textMuted,
    fontSize: font.sm,
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
  error: {
    color: colors.critical,
    fontSize: font.sm,
    marginBottom: spacing.sm,
  },
  btn: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  btnDisabled: {
    opacity: 0.4,
  },
  btnText: {
    color: colors.textPrimary,
    fontSize: font.md,
    fontWeight: '700',
  },
  footer: {
    color: colors.textMuted,
    fontSize: font.xs,
    textAlign: 'center',
  },
});
