import React from 'react';
import {
  Modal, View, Text, TouchableOpacity, ScrollView, StyleSheet, SafeAreaView,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors, spacing, radius, font } from '../theme';

export const FEATURES = [
  // Information
  { id: 'get_current_time_and_date', label: '🕐 Time & Date',     category: 'Information', hasInput: false },
  { id: 'get_safety_tips',           label: '💡 Safety Tips',     category: 'Information', hasInput: true,  placeholder: 'Context: walking, crossing, night, indoor, public_transport' },
  { id: 'get_emergency_info',        label: '🚨 Emergency Info',  category: 'Safety',      hasInput: true,  placeholder: 'Your location (e.g. New Delhi, India)' },
  // Weather
  { id: 'get_current_weather',       label: '🌤 Current Weather', category: 'Weather',     hasInput: true,  placeholder: 'City name (e.g. Mumbai)' },
  { id: 'get_weather_forecast',      label: '🌦 Forecast',        category: 'Weather',     hasInput: true,  placeholder: 'City name (e.g. Mumbai)' },
  // News
  { id: 'get_top_headlines',         label: '📰 Top Headlines',   category: 'News',        hasInput: true,  placeholder: 'Country code (e.g. in, us, gb)' },
  { id: 'search_news',               label: '🔍 Search News',     category: 'News',        hasInput: true,  placeholder: 'Search keyword (e.g. technology)' },
  // Navigation
  { id: 'navigate_to_destination',   label: '🧭 Navigate',        category: 'Navigation',  hasInput: true,  placeholder: 'From → To (e.g. India Gate to Red Fort)' },
  { id: 'find_nearby_places',        label: '📍 Nearby Places',   category: 'Navigation',  hasInput: true,  placeholder: 'Category (e.g. hospital, pharmacy, bus_stop)' },
];

const CATEGORIES = ['Information', 'Weather', 'News', 'Navigation', 'Safety'];

export default function AssistantPanel({ isOpen, onClose, onFeatureSelect }) {
  const press = (fn) => () => {
    Haptics.selectionAsync();
    fn();
  };

  return (
    <Modal visible={isOpen} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.overlay}>
        <SafeAreaView style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.title}>🤖 AI Assistant</Text>
            <TouchableOpacity onPress={press(onClose)} style={styles.closeBtn} accessibilityLabel="Close assistant">
              <Text style={styles.closeText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
            {CATEGORIES.map((cat) => {
              const items = FEATURES.filter((f) => f.category === cat);
              if (!items.length) return null;
              return (
                <View key={cat} style={styles.section}>
                  <Text style={styles.sectionTitle}>{cat}</Text>
                  {items.map((feature) => (
                    <TouchableOpacity
                      key={feature.id}
                      style={styles.featureBtn}
                      onPress={press(() => onFeatureSelect(feature))}
                      accessibilityLabel={feature.label}
                      accessibilityRole="button"
                    >
                      <Text style={styles.featureLabel}>{feature.label}</Text>
                      <Text style={styles.chevron}>›</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              );
            })}
          </ScrollView>
        </SafeAreaView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    maxHeight: '85%',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  title: {
    color: colors.textPrimary,
    fontSize: font.lg,
    fontWeight: '700',
  },
  closeBtn: {
    padding: spacing.sm,
  },
  closeText: {
    color: colors.textSecondary,
    fontSize: font.lg,
  },
  scroll: {
    padding: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  section: {
    marginBottom: spacing.lg,
  },
  sectionTitle: {
    color: colors.textMuted,
    fontSize: font.xs,
    fontWeight: '700',
    letterSpacing: 1.5,
    marginBottom: spacing.sm,
    textTransform: 'uppercase',
  },
  featureBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  featureLabel: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: font.md,
  },
  chevron: {
    color: colors.textMuted,
    fontSize: font.lg,
  },
});
