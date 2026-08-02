export interface User {
  id: string
  email: string
  full_name: string
  organization_id: string
  organization_name: string
  created_at: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface SignupPayload {
  full_name: string
  email: string
  password: string
  organization_name: string
}

export interface VerifyOtpPayload {
  email: string
  otp: string
}

export interface ForgotPasswordPayload {
  email: string
}

export interface ResetPasswordPayload {
  email: string
  otp: string
  new_password: string
}
