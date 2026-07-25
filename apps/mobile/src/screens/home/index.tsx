import { Image } from 'expo-image';
import { router } from 'expo-router';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  useColorScheme,
  View,
} from 'react-native';

import { AdaptiveGlass } from '@/components/adaptive-glass';
import { colors } from '@/constants/colors';
import { useVehicleStatus } from '@/hooks/use-vehicle-status';

function celsiusToFahrenheit(celsius: number) {
  return (celsius * 9) / 5 + 32;
}

function relativeTime(unixSeconds: number) {
  const ageSeconds = Math.max(0, Math.round(Date.now() / 1000 - unixSeconds));
  if (ageSeconds < 5) return 'just now';
  if (ageSeconds < 60) return `${ageSeconds}s ago`;
  return `${Math.round(ageSeconds / 60)}m ago`;
}

export function HomeScreen() {
  useColorScheme();
  const {
    apiKeyConfigured,
    error,
    isLoading,
    isUpdating,
    refresh,
    setEnabled,
    status,
  } = useVehicleStatus();

  const cabinTemperature = status?.cabin
    ? celsiusToFahrenheit(status.cabin.temperature_c)
    : null;
  const isHot =
    cabinTemperature !== null &&
    cabinTemperature >= (status?.automation.threshold_f ?? 105);

  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentInsetAdjustmentBehavior="automatic"
      refreshControl={
        <RefreshControl
          refreshing={isLoading && Boolean(status)}
          onRefresh={() => void refresh()}
        />
      }
      contentContainerStyle={styles.content}>
      <View style={styles.ambientGlow} />

      <View style={styles.statusRow}>
        <View
          style={[
            styles.statusDot,
            { backgroundColor: status?.connected ? colors.green : colors.orange },
          ]}
        />
        <Text selectable style={[styles.caption, { color: colors.secondaryLabel }]}>
          {status?.connected ? 'Comma online' : 'Waiting for comma'}
        </Text>
        <Pressable
          accessibilityLabel="Connection settings"
          hitSlop={12}
          onPress={() => router.push('/settings')}
          style={({ pressed }) => pressed && styles.pressed}>
          <Image
            source="sf:gearshape.fill"
            style={{ width: 23, height: 23 }}
            tintColor={colors.secondaryLabel as string}
          />
        </Pressable>
      </View>

      <AdaptiveGlass style={styles.temperatureCard}>
        <Text style={[styles.eyebrow, { color: colors.secondaryLabel }]}>
          CABIN
        </Text>
        {isLoading && !status ? (
          <ActivityIndicator color={colors.green} size="large" />
        ) : (
          <Text
            selectable
            style={[
              styles.temperature,
              { color: isHot ? colors.orange : colors.label },
            ]}>
            {cabinTemperature === null ? '—' : `${Math.round(cabinTemperature)}°`}
          </Text>
        )}
        <Text selectable style={[styles.caption, { color: colors.secondaryLabel }]}>
          {status?.cabin
            ? `Updated ${relativeTime(status.cabin.received_at_unix)}`
            : 'No temperature reading'}
        </Text>
        {status?.cabin ? (
          <View style={styles.metrics}>
            <Text selectable style={[styles.metric, { color: colors.secondaryLabel }]}>
              {status.cabin.humidity_pct}% humidity
            </Text>
            <Text selectable style={[styles.metric, { color: colors.secondaryLabel }]}>
              {status.cabin.co2_ppm} ppm CO₂
            </Text>
            <Text selectable style={[styles.metric, { color: colors.secondaryLabel }]}>
              {status.cabin.battery_pct}% sensor
            </Text>
          </View>
        ) : null}
      </AdaptiveGlass>

      <AdaptiveGlass style={styles.automationCard}>
        <View style={styles.automationCopy}>
          <Text style={[styles.cardTitle, { color: colors.label }]}>
            Cabin protection
          </Text>
          <Text style={[styles.cardDescription, { color: colors.secondaryLabel }]}>
            Start climate when the cabin reaches{' '}
            {Math.round(status?.automation.threshold_f ?? 105)}°F.
          </Text>
        </View>
        <Switch
          disabled={!status || isUpdating}
          value={status?.automation.enabled ?? false}
          onValueChange={(enabled) => void setEnabled(enabled)}
        />
      </AdaptiveGlass>

      {!apiKeyConfigured ? (
        <Pressable
          onPress={() => router.push('/settings')}
          style={({ pressed }) => pressed && styles.pressed}>
          <AdaptiveGlass interactive style={styles.actionButton}>
            <Text style={[styles.actionText, { color: colors.label }]}>
              Connect to your IONIQ 5
            </Text>
          </AdaptiveGlass>
        </Pressable>
      ) : null}

      {error ? (
        <AdaptiveGlass style={styles.errorCard}>
          <Text selectable style={[styles.errorText, { color: colors.red }]}>
            {error}
          </Text>
        </AdaptiveGlass>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: 18,
    paddingHorizontal: 18,
    paddingBottom: 48,
  },
  ambientGlow: {
    position: 'absolute',
    top: -140,
    left: -80,
    right: -80,
    height: 360,
    borderRadius: 180,
    opacity: 0.28,
    experimental_backgroundImage:
      'radial-gradient(circle at 50% 40%, #62e0b7 0%, rgba(98,224,183,0) 68%)',
  },
  statusRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    minHeight: 36,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  caption: {
    flex: 1,
    fontSize: 14,
  },
  pressed: {
    opacity: 0.65,
  },
  temperatureCard: {
    alignItems: 'center',
    borderCurve: 'continuous',
    borderRadius: 32,
    gap: 8,
    minHeight: 310,
    justifyContent: 'center',
    overflow: 'hidden',
    padding: 28,
  },
  eyebrow: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 1.4,
  },
  temperature: {
    fontSize: 104,
    fontWeight: '200',
    fontVariant: ['tabular-nums'],
    letterSpacing: -7,
    lineHeight: 116,
  },
  metrics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    justifyContent: 'center',
    paddingTop: 12,
  },
  metric: {
    fontSize: 12,
    fontVariant: ['tabular-nums'],
  },
  automationCard: {
    alignItems: 'center',
    borderCurve: 'continuous',
    borderRadius: 24,
    flexDirection: 'row',
    gap: 18,
    overflow: 'hidden',
    padding: 20,
  },
  automationCopy: {
    flex: 1,
    gap: 4,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  cardDescription: {
    fontSize: 14,
    lineHeight: 20,
  },
  actionButton: {
    alignItems: 'center',
    borderCurve: 'continuous',
    borderRadius: 22,
    overflow: 'hidden',
    padding: 18,
  },
  actionText: {
    fontSize: 16,
    fontWeight: '600',
  },
  errorCard: {
    borderCurve: 'continuous',
    borderRadius: 18,
    overflow: 'hidden',
    padding: 16,
  },
  errorText: {
    fontSize: 14,
    lineHeight: 20,
  },
});
