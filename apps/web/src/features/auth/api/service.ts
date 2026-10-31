// ============================================================
// Auth Service — accounts live in the QuFin API (services/api)
// ============================================================
//   POST /v1/auth/sign-up | sign-in | sign-out, GET /v1/auth/me
//
// The session is an httpOnly cookie set by the API; this code never sees
// the token. Without NEXT_PUBLIC_API_URL the app runs on local mock data
// and has no accounts.
// ============================================================

import { ApiError, apiClient, isApiConfigured } from '@/lib/api-client';
import type { Credentials, User } from './types';

export const authEnabled = isApiConfigured;

/** The signed-in user, or null when signed out (or when accounts are disabled). */
export async function getCurrentUser(): Promise<User | null> {
  if (!authEnabled) return null;
  try {
    return await apiClient<User>('/v1/auth/me');
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

export async function signIn(credentials: Credentials): Promise<User> {
  return apiClient<User>('/v1/auth/sign-in', {
    method: 'POST',
    body: JSON.stringify(credentials)
  });
}

export async function signUp(credentials: Credentials): Promise<User> {
  return apiClient<User>('/v1/auth/sign-up', {
    method: 'POST',
    body: JSON.stringify(credentials)
  });
}

export async function signOut(): Promise<void> {
  return apiClient<void>('/v1/auth/sign-out', { method: 'POST' });
}
