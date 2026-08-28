import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types/auth'

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  setAuth: (user: User, accessToken: string) => void
  setAccessToken: (accessToken: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      // Real auth: access token lives only in memory (not persisted) — the
      // refresh token is an httpOnly cookie the server sets, invisible to JS.
      // Session is re-established on page load via POST /auth/refresh.
      setAuth: (user, accessToken) =>
        set({ user, accessToken, isAuthenticated: true }),
      setAccessToken: (accessToken) => set({ accessToken }),
      logout: () =>
        set({ user: null, accessToken: null, isAuthenticated: false }),
    }),
    {
      name: 'ai-coo-auth',
      // Only persist `user` across reloads, for a fast UI paint before the
      // silent refresh resolves. accessToken is NEVER persisted — it's
      // re-fetched fresh via the refresh cookie on load.
      partialize: (state) => ({ user: state.user }),
    }
  )
)
