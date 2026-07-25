import * as SecureStore from 'expo-secure-store';

const API_KEY_STORAGE_KEY = 'ioniq5-api-key';

export const credentials = {
  getApiKey() {
    return SecureStore.getItemAsync(API_KEY_STORAGE_KEY);
  },
  async setApiKey(value: string) {
    const normalized = value.trim();
    if (!normalized) {
      await SecureStore.deleteItemAsync(API_KEY_STORAGE_KEY);
      return;
    }
    await SecureStore.setItemAsync(API_KEY_STORAGE_KEY, normalized);
  },
};

