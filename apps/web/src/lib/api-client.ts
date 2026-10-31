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

/** FastAPI puts a readable message in `detail` (a string, or a list of validation errors). */
async function errorMessage(res: Response) {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') return body.detail;
  } catch {
    // Not JSON: fall through to the status text.
  }
  return `API error: ${res.status} ${res.statusText}`;
}

export async function apiClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  if (!API_URL) throw new Error('NEXT_PUBLIC_API_URL is not set');

  const res = await fetch(`${API_URL}${endpoint}`, {
    // The API is on another origin; send the httpOnly session cookie with every call.
    credentials: 'include',
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers }
  });

  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
