import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types/auth'

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  isDevAccount: boolean
  setAuth: (user: User, accessToken: string) => void
  setAccessToken: (accessToken: string) => void
  logout: () => void
  mockLogin: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isDevAccount: false,
      // Real auth: access token lives only in memory (not persisted) — the
      // refresh token is an httpOnly cookie the server sets, invisible to JS.
      // Session is re-established on page load via POST /auth/refresh.
      setAuth: (user, accessToken) =>
        set({ user, accessToken, isAuthenticated: true, isDevAccount: false }),
      setAccessToken: (accessToken) => set({ accessToken }),
      logout: () =>
        set({ user: null, accessToken: null, isAuthenticated: false, isDevAccount: false }),
      // DEV ONLY — bypasses the real auth flow entirely for local testing.
      // Untouched by the cookie-based refresh flow below.
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
          isAuthenticated: true,
          isDevAccount: true,
        }),
    }),
    {
      name: 'ai-coo-auth',
      // Only persist `user` + isDevAccount across reloads, for a fast UI
      // paint before the silent refresh resolves. accessToken is NEVER
      // persisted — it's re-fetched fresh via the refresh cookie on load.
      partialize: (state) => ({ user: state.user, isDevAccount: state.isDevAccount }),
    }
  )
)
