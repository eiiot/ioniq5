import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState } from 'react-native';

import {
  api,
  type CabinHistorySample,
  type VehicleStatus,
} from '@/services/api';
import { credentials } from '@/services/credentials';

const REFRESH_INTERVAL_MS = 15_000;

export function useVehicleStatus() {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [status, setStatus] = useState<VehicleStatus | null>(null);
  const [history, setHistory] = useState<CabinHistorySample[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async (keyOverride?: string | null) => {
    const key = keyOverride === undefined ? apiKey : keyOverride;
    if (!key) {
      setStatus(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    try {
      const [nextStatus, historyResponse] = await Promise.all([
        api.getStatus(key),
        api.getHistory(key),
      ]);
      if (!mounted.current) return;
      setStatus(nextStatus);
      setHistory(historyResponse.history);
      setError(null);
    } catch (caughtError) {
      if (!mounted.current) return;
      setError(
        caughtError instanceof Error ? caughtError.message : 'Unable to connect',
      );
    } finally {
      if (mounted.current) setIsLoading(false);
    }
  }, [apiKey]);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      credentials.getApiKey().then((storedKey) => {
        if (cancelled) return;
        setApiKey(storedKey);
        setIsLoading(true);
        void refresh(storedKey);
      });
      return () => {
        cancelled = true;
      };
    }, [refresh]),
  );

  useEffect(() => {
    if (!apiKey) return;
    const interval = setInterval(() => void refresh(), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [apiKey, refresh]);

  useEffect(() => {
    if (!apiKey) return;
    const subscription = AppState.addEventListener('change', (nextState) => {
      if (nextState === 'active') void refresh();
    });
    return () => subscription.remove();
  }, [apiKey, refresh]);

  const setEnabled = useCallback(
    async (enabled: boolean) => {
      if (!apiKey || !status) return;
      const previousStatus = status;
      setStatus({
        ...status,
        automation: { ...status.automation, enabled },
      });
      setIsUpdating(true);
      try {
        const nextStatus = await api.setAutomationEnabled(apiKey, enabled);
        setStatus(nextStatus);
        setError(null);
      } catch (caughtError) {
        setStatus(previousStatus);
        setError(
          caughtError instanceof Error
            ? caughtError.message
            : 'Unable to update',
        );
      } finally {
        setIsUpdating(false);
      }
    },
    [apiKey, status],
  );

  return {
    apiKeyConfigured: Boolean(apiKey),
    error,
    history,
    isLoading,
    isUpdating,
    refresh,
    setEnabled,
    status,
  };
}
