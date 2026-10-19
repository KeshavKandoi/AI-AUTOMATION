import { apiClient } from './client'
import type {
  LoginPayload,
  SignupPayload,
  VerifyOtpPayload,
  ForgotPasswordPayload,
  ResetPasswordPayload,
  ChangePasswordPayload,
  User,
} from '@/types/auth'


const authRequest = { baseURL: import.meta.env.PROD ? '/' : import.meta.env.VITE_API_BASE_URL }

export const authApi = {
  login: (payload: LoginPayload) =>
    apiClient.post<{ user: User; access_token: string }>('/auth/login', payload, authRequest),

  signup: (payload: SignupPayload) =>
    apiClient.post<{ message: string; email: string }>('/auth/signup', payload),

  verifyOtp: (payload: VerifyOtpPayload) =>
    apiClient.post<{ user: User; access_token: string }>('/auth/verify-otp', payload, authRequest),

  resendOtp: (email: string) =>
    apiClient.post<{ message: string }>('/auth/resend-otp', { email }),

  forgotPassword: (payload: ForgotPasswordPayload) =>
    apiClient.post<{ message: string }>('/auth/forgot-password', payload),

  resetPassword: (payload: ResetPasswordPayload) =>
    apiClient.post<{ message: string }>('/auth/reset-password', payload),

  resendResetOtp: (email: string) =>
    apiClient.post<{ message: string }>('/auth/resend-reset-otp', { email }),

  me: () => apiClient.get<User>('/auth/me'),

  changePassword: (payload: ChangePasswordPayload) =>
    apiClient.post<{ message: string }>('/auth/change-password', payload),
  logout: () => apiClient.post('/auth/logout', {}, authRequest),
  deleteAccount: (password: string) =>
    apiClient.post<{ message: string }>('/account/delete', { password }),
}
