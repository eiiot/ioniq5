import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { AdaptiveGlass } from '@/components/adaptive-glass';
import { API_BASE_URL } from '@/constants/api';
import { colors } from '@/constants/colors';
import { credentials } from '@/services/credentials';

export function SettingsScreen() {
  const [apiKey, setApiKey] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    credentials.getApiKey().then((storedKey) => {
      setApiKey(storedKey ?? '');
      setIsLoading(false);
    });
  }, []);

  async function save() {
    setIsSaving(true);
    try {
      await credentials.setApiKey(apiKey);
      router.back();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={process.env.EXPO_OS === 'ios' ? 'padding' : undefined} style={styles.root}>
      <ScrollView
        contentInsetAdjustmentBehavior="automatic"
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={styles.content}>
        <AdaptiveGlass style={styles.card}>
          <View style={styles.copy}>
            <Text style={[styles.title, { color: colors.label }]}>API access</Text>
            <Text style={[styles.description, { color: colors.secondaryLabel }]}>
              The key authorizes this device to control your comma at{' '}
              <Text selectable>{API_BASE_URL}</Text>. It is stored in the iOS
              Keychain and never bundled into the app.
            </Text>
          </View>

          {isLoading ? (
            <ActivityIndicator color={colors.green} />
          ) : (
            <TextInput
              autoCapitalize="none"
              autoCorrect={false}
              onChangeText={setApiKey}
              placeholder="Paste API key"
              placeholderTextColor={colors.tertiaryLabel}
              secureTextEntry
              selectionColor={colors.green}
              style={[
                styles.input,
                { color: colors.label, borderColor: colors.tertiaryLabel },
              ]}
              value={apiKey}
            />
          )}

          <Pressable
            disabled={isLoading || isSaving}
            onPress={() => void save()}
            style={({ pressed }) => [
              styles.saveButton,
              { backgroundColor: colors.green },
              pressed && styles.pressed,
            ]}>
            {isSaving ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.saveText}>Save connection</Text>
            )}
          </Pressable>
        </AdaptiveGlass>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  content: {
    gap: 16,
    padding: 18,
  },
  card: {
    borderCurve: 'continuous',
    borderRadius: 28,
    gap: 24,
    overflow: 'hidden',
    padding: 22,
  },
  copy: {
    gap: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
  },
  description: {
    fontSize: 15,
    lineHeight: 22,
  },
  input: {
    borderCurve: 'continuous',
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    fontFamily: 'ui-monospace',
    fontSize: 15,
    minHeight: 50,
    paddingHorizontal: 14,
  },
  saveButton: {
    alignItems: 'center',
    borderCurve: 'continuous',
    borderRadius: 14,
    minHeight: 50,
    justifyContent: 'center',
    paddingHorizontal: 18,
  },
  saveText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  pressed: {
    opacity: 0.72,
  },
});

