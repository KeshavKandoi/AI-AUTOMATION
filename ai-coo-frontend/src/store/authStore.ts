import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types/auth'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setAuth: (user: User, accessToken: string, refreshToken: string) => void
  logout: () => void
  mockLogin: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setAuth: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken, isAuthenticated: true }),
      logout: () =>
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),
      // DEV ONLY — remove once real /auth/* endpoints exist on the backend
      mockLogin: () =>
        set({
          user: {
            id: 'dev-user',
            email: 'keshav@dev.local',
            full_name: 'Keshav Kandoi',
            organization_id: '8cade9c9-3e2d-4fb6-9f83-276a55275bc6',
            organization_name: 'AI COO (dev)',
            created_at: new Date().toISOString(),
          },
          accessToken: 'dev-mock-token',
          refreshToken: 'dev-mock-refresh',
          isAuthenticated: true,
        }),
    }),
    { name: 'ai-coo-auth' }
  )
)
