import { BlurView } from 'expo-blur';
import {
  GlassView,
  isGlassEffectAPIAvailable,
  isLiquidGlassAvailable,
} from 'expo-glass-effect';
import type { PropsWithChildren } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';

type AdaptiveGlassProps = PropsWithChildren<{
  interactive?: boolean;
  style?: StyleProp<ViewStyle>;
}>;

export function AdaptiveGlass({
  children,
  interactive = false,
  style,
}: AdaptiveGlassProps) {
  if (isLiquidGlassAvailable() && isGlassEffectAPIAvailable()) {
    return (
      <GlassView isInteractive={interactive} style={style}>
        {children}
      </GlassView>
    );
  }

  return (
    <BlurView intensity={90} tint="systemMaterial" style={style}>
      {children}
    </BlurView>
  );
}

