import axios from 'axios'
import { useAuthStore } from '@/store/authStore'


const PUBLIC_PATHS = ['/', '/features', '/how-it-works', '/connections', '/google-data', '/login', '/signup', '/verify-otp', '/forgot-password', '/reset-password', '/privacy', '/terms', '/security']

export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.includes(pathname)
}

// Keep production API calls on the same backend used by the /auth Vercel proxy.
const apiBaseUrl = import.meta.env.PROD
  ? 'https://ai-automation-sg.onrender.com'
  : import.meta.env.VITE_API_BASE_URL

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(
        import.meta.env.PROD ? '/auth/refresh' : `${apiBaseUrl}/auth/refresh`,
        {},
        { withCredentials: true, timeout: 30_000 }
      )
      .then((res) => {
        const { access_token, user } = res.data
        useAuthStore.getState().setAuth(user, access_token)
        return access_token as string
      })
      .catch((error) => {

        if (axios.isAxiosError(error) && error.response?.status === 401) {
          useAuthStore.getState().logout()
        }
        return null
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}



export function restoreSession(): Promise<string | null> {
  return refreshAccessToken()
}

apiClient.interceptors.request.use(async (config) => {
  if (config.url === '/auth/refresh') return config
  const state = useAuthStore.getState()
  const protectedPage = !isPublicPath(window.location.pathname)
  const token = state.accessToken || (protectedPage && state.user ? await refreshAccessToken() : null)
  if (protectedPage && state.user && !token) throw new Error('Session expired')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (
      error.response?.status === 401 &&
      original?.url === '/auth/change-password' &&
      error.response?.data?.detail === 'Current password is incorrect'
    ) {
      return Promise.reject(error)
    }

    if (error.response?.status === 401 && !original?._retried && !isPublicPath(window.location.pathname)) {
      original._retried = true
      const newToken = await refreshAccessToken()
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return apiClient(original)
      }
    }

    if (error.response?.status === 401 && !isPublicPath(window.location.pathname) && !useAuthStore.getState().user) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
