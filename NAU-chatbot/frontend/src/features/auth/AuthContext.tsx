import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { authApi } from "../../api/auth";
import { configureTokenRefresh, setAccessToken } from "../../api/http";
import type { AuthUser, SignupRequest } from "../../types/auth";

let refreshInFlight: ReturnType<typeof authApi.refresh> | null = null;

type AuthStatus = "checking" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: AuthStatus;
  isAuthenticated: boolean;
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<AuthUser>;
  signup: (payload: SignupRequest) => Promise<AuthUser>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readCsrfToken(): string | null {
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("iit_csrf="));
  if (!cookie) return null;
  try {
    return decodeURIComponent(cookie.slice("iit_csrf=".length));
  } catch {
    return null;
  }
}

function requestTokenRefresh(csrfToken: string) {
  refreshInFlight ??= authApi.refresh(csrfToken).finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<AuthUser | null>(null);

  const clearSession = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  const refreshAccess = useCallback(async (): Promise<string | null> => {
    const csrfToken = readCsrfToken();
    if (!csrfToken) {
      clearSession();
      return null;
    }
    try {
      const response = await requestTokenRefresh(csrfToken);
      setAccessToken(response.access_token);
      setUser(response.user);
      setStatus("authenticated");
      return response.access_token;
    } catch {
      clearSession();
      return null;
    }
  }, [clearSession]);

  useEffect(() => {
    configureTokenRefresh(refreshAccess);
    void refreshAccess();
    return () => configureTokenRefresh(null);
  }, [refreshAccess]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await authApi.login({ username, password });
    setAccessToken(response.access_token);
    setUser(response.user);
    setStatus("authenticated");
    return response.user;
  }, []);

  const signup = useCallback(async (payload: SignupRequest) => {
    const response = await authApi.signup(payload);
    setAccessToken(response.access_token);
    setUser(response.user);
    setStatus("authenticated");
    return response.user;
  }, []);

  const logout = useCallback(async () => {
    const csrfToken = readCsrfToken();
    try {
      if (csrfToken) await authApi.logout(csrfToken);
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, isAuthenticated: status === "authenticated", user, login, signup, logout }),
    [login, logout, signup, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
