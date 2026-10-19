export type ThemePreference = 'dark' | 'light' | 'system'

const STORAGE_KEY = 'ai-coo-theme'

function systemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function resolveEffectiveTheme(pref: ThemePreference): 'dark' | 'light' {
  if (pref === 'system') return systemPrefersDark() ? 'dark' : 'light'
  return pref
}


export function applyTheme(pref: ThemePreference) {
  const effective = resolveEffectiveTheme(pref)
  if (effective === 'light') {
    document.documentElement.setAttribute('data-theme', 'light')
  } else {
    document.documentElement.removeAttribute('data-theme')
  }
}

export function getStoredTheme(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark' || stored === 'light' || stored === 'system') return stored
  return 'system'
}

export function setStoredTheme(pref: ThemePreference) {
  localStorage.setItem(STORAGE_KEY, pref)
  applyTheme(pref)
}


export function initTheme() {
  const pref = getStoredTheme()
  applyTheme(pref)

  if (pref === 'system') {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const listener = () => applyTheme('system')
    mq.addEventListener('change', listener)
  }
}
