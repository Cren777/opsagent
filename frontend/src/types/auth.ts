export interface AuthUser {
  id: string
  username: string
  role: string
  is_active: boolean
  created_at: string
  updated_at: string
  last_login_at?: string | null
}

export interface BootstrapResponse {
  registration_open: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
  user: AuthUser
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
}

export interface UpdateProfileRequest {
  username: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}
