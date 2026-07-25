import { Color } from 'expo-router';
import { Platform } from 'react-native';

export const colors = {
  background: Platform.select({
    ios: Color.ios.systemBackground,
    android: Color.android.dynamic.surface,
    default: '#eef4f2',
  })!,
  label: Platform.select({
    ios: Color.ios.label,
    android: Color.android.dynamic.onSurface,
    default: '#14211d',
  })!,
  secondaryLabel: Platform.select({
    ios: Color.ios.secondaryLabel,
    android: Color.android.dynamic.onSurfaceVariant,
    default: '#52615c',
  })!,
  tertiaryLabel: Platform.select({
    ios: Color.ios.tertiaryLabel,
    android: Color.android.dynamic.outline,
    default: '#76847f',
  })!,
  green: Platform.select({
    ios: Color.ios.systemGreen,
    android: Color.android.dynamic.primary,
    default: '#23855b',
  })!,
  orange: Platform.select({
    ios: Color.ios.systemOrange,
    android: Color.android.material.primary70,
    default: '#d87614',
  })!,
  red: Platform.select({
    ios: Color.ios.systemRed,
    android: Color.android.material.error,
    default: '#d13c3c',
  })!,
};

