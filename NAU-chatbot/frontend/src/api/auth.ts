import type { LoginRequest, LogoutResponse, SignupRequest, TokenResponse } from "../types/auth";
import { apiRequest } from "./http";

export const authApi = {
  login(payload: LoginRequest): Promise<TokenResponse> {
    return apiRequest<TokenResponse>("/auth/login", {
      method: "POST",
      body: payload,
      auth: false,
      retryAuth: false,
    });
  },

  signup(payload: SignupRequest): Promise<TokenResponse> {
    return apiRequest<TokenResponse>("/auth/signup", {
      method: "POST",
      body: payload,
      auth: false,
      retryAuth: false,
    });
  },

  refresh(csrfToken: string): Promise<TokenResponse> {
    return apiRequest<TokenResponse>("/auth/refresh", {
      method: "POST",
      headers: { "X-CSRF-Token": csrfToken },
      auth: false,
      retryAuth: false,
    });
  },

  logout(csrfToken: string): Promise<LogoutResponse> {
    return apiRequest<LogoutResponse>("/auth/logout", {
      method: "POST",
      headers: { "X-CSRF-Token": csrfToken },
      auth: false,
      retryAuth: false,
    });
  },
};
