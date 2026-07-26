import { useMemo } from 'react';
import { Text, useWindowDimensions, View } from 'react-native';

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
  const range = Math.max(ceiling - floor, 1);
  const coordinates = values.map((value, index) => ({
    x: (index / (values.length - 1)) * width,
    y: ((ceiling - value) / range) * CHART_HEIGHT,
  }));

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
        style={{ height: CHART_HEIGHT, width }}>
        {[0, 0.5, 1].map((position) => (
          <View
            key={position}
            style={{
              backgroundColor: colors.separator,
              height: 0.5,
              left: 0,
              position: 'absolute',
              right: 0,
              top: position * CHART_HEIGHT,
            }}
          />
        ))}
        {coordinates.slice(1).map((point, index) => {
          const previous = coordinates[index];
          const deltaX = point.x - previous.x;
          const deltaY = point.y - previous.y;
          const length = Math.sqrt(deltaX ** 2 + deltaY ** 2);
          const angle = Math.atan2(deltaY, deltaX);
          return (
            <View
              key={`${points[index + 1].at_unix}`}
              style={{
                backgroundColor: colors.blue,
                borderRadius: 1,
                height: 2,
                left: (previous.x + point.x - length) / 2,
                position: 'absolute',
                top: (previous.y + point.y - 2) / 2,
                transform: [{ rotate: `${angle}rad` }],
                width: length,
              }}
            />
          );
        })}
      </View>
    </View>
  );
}
