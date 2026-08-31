import { API_BASE_URL } from "../config/env";
import type { ApiErrorEnvelope } from "../types/api";

type RefreshHandler = () => Promise<string | null>;

let accessToken: string | null = null;
let refreshHandler: RefreshHandler | null = null;
let refreshPromise: Promise<string | null> | null = null;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryAfter?: number;

  constructor(message: string, status = 0, code = "NETWORK_ERROR", retryAfter?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function configureTokenRefresh(handler: RefreshHandler | null): void {
  refreshHandler = handler;
}

interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  auth?: boolean;
  retryAuth?: boolean;
}

function safeError(payload: unknown, status: number, retryAfter?: number): ApiError {
  const envelope = (payload ?? {}) as ApiErrorEnvelope;
  const code = envelope.error?.code ?? (status === 422 ? "VALIDATION_ERROR" : "REQUEST_FAILED");
  let message = envelope.error?.message;

  if (!message && typeof envelope.detail === "string") {
    message = envelope.detail;
  }
  if (!message && status === 422) {
    message = "Certains champs sont invalides. Vérifiez le formulaire.";
  }
  if (!message && status === 401) {
    message = "Votre session a expiré. Reconnectez-vous.";
  }
  if (!message && status === 403) {
    message = "Vous n’êtes pas autorisé à effectuer cette action.";
  }
  if (!message && status === 429) {
    message = "Trop de requêtes. Patientez un instant puis réessayez.";
  }
  if (!message && status >= 500) {
    message = "Le service est temporairement indisponible.";
  }

  return new ApiError(message ?? "La requête n’a pas abouti.", status, code, retryAfter);
}

async function parsePayload(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined;
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

async function performRequest<T>(path: string, options: ApiRequestOptions, token: string | null): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body !== undefined && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");
  if (options.auth !== false && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      body:
        options.body === undefined
          ? undefined
          : options.body instanceof FormData
            ? options.body
            : JSON.stringify(options.body),
      credentials: "include",
      headers,
    });
  } catch {
    throw new ApiError("Connexion au serveur impossible. Vérifiez votre réseau.");
  }

  const payload = await parsePayload(response);
  if (!response.ok) {
    const retryHeader = response.headers.get("Retry-After");
    const retryAfter = retryHeader ? Number.parseInt(retryHeader, 10) : undefined;
    throw safeError(payload, response.status, Number.isFinite(retryAfter) ? retryAfter : undefined);
  }
  return payload as T;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  try {
    return await performRequest<T>(path, options, accessToken);
  } catch (error) {
    const mayRefresh =
      error instanceof ApiError &&
      error.status === 401 &&
      options.auth !== false &&
      options.retryAuth !== false &&
      refreshHandler !== null;

    if (!mayRefresh) throw error;

    refreshPromise ??= refreshHandler!().finally(() => {
      refreshPromise = null;
    });
    const refreshedToken = await refreshPromise;
    if (!refreshedToken) throw error;
    return performRequest<T>(path, { ...options, retryAuth: false }, refreshedToken);
  }
}
