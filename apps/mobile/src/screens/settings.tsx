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
} from 'react-native';

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
        style={{ backgroundColor: colors.background }}
        contentInsetAdjustmentBehavior="automatic"
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={styles.content}>
        <Text style={[styles.description, { color: colors.secondaryLabel }]}>
          Enter the key for <Text selectable>{API_BASE_URL}</Text>. It is stored
          in the iOS Keychain.
        </Text>

        {isLoading ? (
          <ActivityIndicator />
        ) : (
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            onChangeText={setApiKey}
            placeholder="API key"
            placeholderTextColor={colors.tertiaryLabel}
            secureTextEntry
            selectionColor={colors.blue}
            style={[
              styles.input,
              {
                color: colors.label,
                backgroundColor: colors.fieldBackground,
              },
            ]}
            value={apiKey}
          />
        )}

        <Pressable
          disabled={isLoading || isSaving}
          onPress={() => void save()}
          style={({ pressed }) => pressed && styles.pressed}>
          {isSaving ? (
            <ActivityIndicator />
          ) : (
            <Text style={[styles.saveText, { color: colors.blue }]}>Save</Text>
          )}
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  content: {
    gap: 24,
    padding: 20,
  },
  description: {
    fontSize: 15,
    lineHeight: 22,
  },
  input: {
    borderCurve: 'continuous',
    borderRadius: 10,
    fontFamily: 'ui-monospace',
    fontSize: 15,
    minHeight: 44,
    paddingHorizontal: 14,
  },
  saveText: {
    fontSize: 17,
  },
  pressed: {
    opacity: 0.72,
  },
});
