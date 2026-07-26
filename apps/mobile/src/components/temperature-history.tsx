import { useMemo } from 'react';
import { Text, useWindowDimensions, View } from 'react-native';
import { LineChart } from 'react-native-chart-kit';

import { colors } from '@/constants/colors';
import type { CabinHistorySample } from '@/services/api';

const CHART_HEIGHT = 104;
const MAX_POINTS = 72;

function fahrenheit(celsius: number) {
  return (celsius * 9) / 5 + 32;
}

export function TemperatureHistory({
  samples,
}: {
  samples: CabinHistorySample[];
}) {
  const { width: windowWidth } = useWindowDimensions();
  const width = Math.max(240, Math.min(windowWidth - 40, 520));
  const points = useMemo(() => {
    if (samples.length <= MAX_POINTS) return samples;
    const stride = (samples.length - 1) / (MAX_POINTS - 1);
    return Array.from(
      { length: MAX_POINTS },
      (_, index) => samples[Math.round(index * stride)],
    );
  }, [samples]);

  if (points.length < 2) {
    return (
      <View style={{ gap: 4 }}>
        <Text style={{ color: colors.label, fontSize: 17 }}>
          Cabin Temperature
        </Text>
        <Text style={{ color: colors.secondaryLabel, fontSize: 15 }}>
          History will appear after a few minutes.
        </Text>
      </View>
    );
  }

  const values = points.map((point) => fahrenheit(point.temperature_c));
  const floor = Math.floor(Math.min(...values) - 2);
  const ceiling = Math.ceil(Math.max(...values) + 2);

  return (
    <View style={{ gap: 10 }}>
      <View
        style={{
          alignItems: 'baseline',
          flexDirection: 'row',
          justifyContent: 'space-between',
        }}>
        <Text style={{ color: colors.label, fontSize: 17 }}>
          Cabin Temperature
        </Text>
        <Text
          style={{
            color: colors.secondaryLabel,
            fontSize: 13,
            fontVariant: ['tabular-nums'],
          }}>
          {floor}°–{ceiling}° · 24h
        </Text>
      </View>
      <View
        accessibilityLabel="24 hour cabin temperature history"
        style={{ height: CHART_HEIGHT, overflow: 'hidden', width }}>
        <LineChart
          chartConfig={{
            backgroundGradientFrom: 'transparent',
            backgroundGradientTo: 'transparent',
            color: () => '#007aff',
            decimalPlaces: 1,
            fillShadowGradientFromOpacity: 0,
            fillShadowGradientToOpacity: 0,
            propsForDots: { r: '0' },
            strokeWidth: 2,
          }}
          data={{
            labels: [],
            datasets: [{ data: values }],
          }}
          height={CHART_HEIGHT}
          style={{ paddingRight: 0, paddingTop: 0 }}
          transparent
          withDots={false}
          withHorizontalLabels={false}
          withHorizontalLines={false}
          withOuterLines={false}
          withShadow={false}
          withVerticalLabels={false}
          withVerticalLines={false}
          width={width}
        />
      </View>
    </View>
  );
}
