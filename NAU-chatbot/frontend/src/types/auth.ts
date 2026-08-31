export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer" | string;
  expires_in: number;
  csrf_token: string;
}

export interface LogoutResponse {
  logged_out: boolean;
}
