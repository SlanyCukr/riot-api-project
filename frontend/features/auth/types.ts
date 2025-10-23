// Authentication types

export interface User {
  id: number;
  email: string;
  display_name: string;
  is_active: boolean;
  is_admin: boolean;
  email_verified: boolean;
  email_verified_at: string | null;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}
