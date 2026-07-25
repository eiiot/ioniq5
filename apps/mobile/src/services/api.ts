import { fetch } from 'expo/fetch';

import { API_BASE_URL } from '@/constants/api';

export type CabinReading = {
  battery_pct: number;
  co2_ppm: number;
  humidity_pct: number;
  measurement_age_s: number;
  received_at_unix: number;
  rssi_dbm: number;
  temperature_c: number;
};

export type VehicleStatus = {
  automation: {
    enabled: boolean;
    threshold_f: number;
  };
  cabin: CabinReading | null;
  connected: boolean;
  last_climate_request: {
    at_unix: number;
    outcome: string;
  } | null;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  apiKey: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${apiKey}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { error?: string }
      | null;
    throw new ApiError(
      payload?.error ?? `Request failed (${response.status})`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

export const api = {
  getStatus(apiKey: string) {
    return request<VehicleStatus>('/v1/status', apiKey);
  },
  setAutomationEnabled(apiKey: string, enabled: boolean) {
    return request<VehicleStatus>('/v1/config', apiKey, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
  },
};

