import { readCookie } from "../utils/cookies";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(message: string, status: number, details: unknown) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

async function parseJsonOrNull(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function refreshTokens(): Promise<boolean> {
  const csrf = readCookie("hl_csrf");
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: csrf ? { "X-CSRF-Token": csrf } : undefined
  });
  return response.ok;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  retry = true
): Promise<T> {
  const method = (init.method || "GET").toUpperCase();
  const csrf = readCookie("hl_csrf");
  const headers = new Headers(init.headers || {});

  if (!headers.has("Content-Type") && method !== "GET" && method !== "HEAD") {
    headers.set("Content-Type", "application/json");
  }

  if (!["GET", "HEAD", "OPTIONS"].includes(method) && csrf) {
    headers.set("X-CSRF-Token", csrf);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    method,
    credentials: "include",
    headers
  });

  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return apiRequest<T>(path, init, false);
    }
  }

  if (!response.ok) {
    const details = await parseJsonOrNull(response);
    throw new ApiError(
      `Request failed (${response.status})`,
      response.status,
      details
    );
  }

  return (await parseJsonOrNull(response)) as T;
}
