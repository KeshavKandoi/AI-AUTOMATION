import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

// Routes that don't require a session. The bootstrap silent-refresh call in
// App.tsx runs on every page load regardless of route, including these, so an
// expected 401 here (visitor has no session) must not force-navigate them
// away from a page that was never supposed to require login.
const PUBLIC_PATHS = ['/', '/login', '/signup', '/verify-otp', '/forgot-password', '/reset-password', '/privacy', '/terms']

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.includes(pathname)
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // sends/receives the httpOnly refresh_token cookie
})

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(
        `${import.meta.env.VITE_API_BASE_URL}/auth/refresh`,
        {},
        { withCredentials: true }
      )
      .then((res) => {
        const { access_token, user } = res.data
        useAuthStore.getState().setAuth(user, access_token)
        return access_token as string
      })
      .catch(() => {
        useAuthStore.getState().logout()
        return null
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const { isDevAccount } = useAuthStore.getState()

    // Dev Account never has a real session or refresh cookie — don't attempt
    // refresh for it, just fall through to the existing 401 -> logout/redirect.
    if (error.response?.status === 401 && !original?._retried && !isDevAccount) {
      original._retried = true
      const newToken = await refreshAccessToken()
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return apiClient(original)
      }
    }

    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      if (!isPublicPath(window.location.pathname)) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
