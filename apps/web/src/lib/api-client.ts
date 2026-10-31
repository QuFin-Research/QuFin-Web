// Base URL of the QuFin API (services/api), e.g. http://localhost:8000.
// When unset, feature services fall back to their local mock data.
const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') || undefined;

export const isApiConfigured = API_URL !== undefined;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  if (!API_URL) throw new Error('NEXT_PUBLIC_API_URL is not set');

  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers }
  });

  if (!res.ok) {
    throw new ApiError(res.status, `API error: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<T>;
}
