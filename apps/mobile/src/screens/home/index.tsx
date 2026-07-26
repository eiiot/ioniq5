import { Image } from 'expo-image';
import { router, Stack } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  useColorScheme,
  View,
} from 'react-native';

import { colors } from '@/constants/colors';
import { TemperatureHistory } from '@/components/temperature-history';
import { useVehicleStatus } from '@/hooks/use-vehicle-status';

function celsiusToFahrenheit(celsius: number) {
  return (celsius * 9) / 5 + 32;
}

function relativeTime(unixSeconds: number, nowUnixSeconds: number) {
  const ageSeconds = Math.max(0, Math.floor(nowUnixSeconds - unixSeconds));
  if (ageSeconds < 5) return 'Now';
  if (ageSeconds < 60) return `${ageSeconds} sec ago`;
  return `${Math.round(ageSeconds / 60)} min ago`;
}

export function HomeScreen() {
  useColorScheme();
  const [nowUnixSeconds, setNowUnixSeconds] = useState<number | null>(null);
  const {
    apiKeyConfigured,
    error,
    history,
    isLoading,
    isUpdating,
    setEnabled,
    status,
  } = useVehicleStatus();

  useEffect(() => {
    const initialTick = setTimeout(
      () => setNowUnixSeconds(Date.now() / 1000),
      0,
    );
    const interval = setInterval(
      () => setNowUnixSeconds(Date.now() / 1000),
      1_000,
    );
    return () => {
      clearTimeout(initialTick);
      clearInterval(interval);
    };
  }, []);

  const cabinTemperature = status?.cabin
    ? celsiusToFahrenheit(status.cabin.temperature_c)
    : null;

  return (
    <>
      <Stack.Screen
        options={{
          headerRight: () => (
            <Pressable
              accessibilityLabel="Settings"
              hitSlop={12}
              onPress={() => router.push('/settings')}>
              <Image
                source="sf:gearshape"
                style={styles.gear}
                tintColor={colors.blue as string}
              />
            </Pressable>
          ),
        }}
      />
      <ScrollView
        style={{ backgroundColor: colors.background }}
        contentInsetAdjustmentBehavior="automatic"
        contentContainerStyle={styles.content}>
        <View style={styles.connection}>
          <View
            style={[
              styles.statusDot,
              {
                backgroundColor: status?.connected
                  ? colors.green
                  : colors.secondaryLabel,
              },
            ]}
          />
          <Text style={[styles.secondary, { color: colors.secondaryLabel }]}>
            {status?.connected ? 'Connected' : 'Not connected'}
          </Text>
        </View>

        <View style={styles.temperature}>
          {isLoading && !status ? (
            <ActivityIndicator />
          ) : (
            <Text
              selectable
              style={[styles.temperatureValue, { color: colors.label }]}>
              {cabinTemperature === null
                ? '—'
                : `${Math.round(cabinTemperature)}°`}
            </Text>
          )}
          <Text
            selectable
            style={[styles.secondary, { color: colors.secondaryLabel }]}>
            {status?.cabin
              ? `${Math.round(status.cabin.humidity_pct)}% humidity`
              : 'No temperature reading'}
          </Text>
          {status?.cabin ? (
            <Text style={[styles.tertiary, { color: colors.tertiaryLabel }]}>
              Updated{' '}
              {relativeTime(
                status.cabin.received_at_unix,
                nowUnixSeconds ?? status.cabin.received_at_unix,
              )}
            </Text>
          ) : null}
        </View>

        <View style={[styles.separator, { backgroundColor: colors.separator }]} />

        <TemperatureHistory samples={history} />

        <View style={[styles.separator, { backgroundColor: colors.separator }]} />

        <View style={styles.row}>
          <View style={styles.rowCopy}>
            <Text style={[styles.rowTitle, { color: colors.label }]}>
              Cabin Protection
            </Text>
            <Text style={[styles.secondary, { color: colors.secondaryLabel }]}>
              Starts at {Math.round(status?.automation.threshold_f ?? 105)}°F
            </Text>
          </View>
          <Switch
            disabled={!status || isUpdating}
            value={status?.automation.enabled ?? false}
            onValueChange={(enabled) => void setEnabled(enabled)}
          />
        </View>

        {!apiKeyConfigured ? (
          <Pressable onPress={() => router.push('/settings')}>
            <Text style={[styles.link, { color: colors.blue }]}>
              Configure Connection
            </Text>
          </Pressable>
        ) : null}

        {error ? (
          <Text selectable style={[styles.error, { color: colors.red }]}>
            {error}
          </Text>
        ) : null}
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: 24,
    paddingHorizontal: 20,
    paddingBottom: 48,
  },
  gear: {
    height: 22,
    width: 22,
  },
  connection: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 7,
  },
  statusDot: {
    borderRadius: 4,
    height: 8,
    width: 8,
  },
  temperature: {
    alignItems: 'center',
    gap: 6,
    justifyContent: 'center',
    minHeight: 240,
  },
  temperatureValue: {
    fontSize: 82,
    fontVariant: ['tabular-nums'],
    fontWeight: '300',
    letterSpacing: -4,
  },
  secondary: {
    fontSize: 15,
  },
  tertiary: {
    fontSize: 13,
  },
  separator: {
    height: StyleSheet.hairlineWidth,
  },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    minHeight: 56,
  },
  rowCopy: {
    flex: 1,
    gap: 3,
  },
  rowTitle: {
    fontSize: 17,
  },
  link: {
    fontSize: 17,
  },
  error: {
    fontSize: 14,
    lineHeight: 20,
  },
});
