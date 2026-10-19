import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initTheme } from '@/lib/theme'

initTheme()



window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault()
  const lastReload = Number(sessionStorage.getItem('route-chunk-reload') || 0)
  if (Date.now() - lastReload > 30_000) {
    sessionStorage.setItem('route-chunk-reload', String(Date.now()))
    window.location.reload()
  }
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
