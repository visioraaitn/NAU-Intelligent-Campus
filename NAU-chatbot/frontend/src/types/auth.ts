export interface LoginRequest {
  username: string;
  password: string;
}

export type UserRole = "USER" | "ADMIN";

export interface AuthUser {
  id: string | null;
  name: string;
  email: string | null;
  role: UserRole;
}

export interface SignupRequest {
  name: string;
  email: string;
  password: string;
  password_confirmation: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer" | string;
  expires_in: number;
  csrf_token: string;
  user: AuthUser;
}

export interface LogoutResponse {
  logged_out: boolean;
}
