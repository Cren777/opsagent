import client from './client'
import type {
  AuthResponse,
  AuthUser,
  BootstrapResponse,
  ChangePasswordRequest,
  LoginRequest,
  RegisterRequest,
  UpdateProfileRequest,
} from '@/types/auth'

export function getAuthBootstrap() {
  return client.get<BootstrapResponse>('/api/auth/bootstrap')
}

export function registerFirstUser(data: RegisterRequest) {
  return client.post<AuthResponse>('/api/auth/register', data)
}

export function login(data: LoginRequest) {
  return client.post<AuthResponse>('/api/auth/login', data)
}

export function fetchCurrentUser() {
  return client.get<AuthUser>('/api/auth/me')
}

export function updateProfile(data: UpdateProfileRequest) {
  return client.patch<AuthUser>('/api/auth/me', data)
}

export function changePassword(data: ChangePasswordRequest) {
  return client.post<{ ok: boolean }>('/api/auth/change-password', data)
}
