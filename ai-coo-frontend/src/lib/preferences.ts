const EMAIL_KEY = 'ai-coo-pref-email-notifications'
const IN_APP_KEY = 'ai-coo-pref-in-app-notifications'


export function getEmailNotificationsEnabled(): boolean {
  const v = localStorage.getItem(EMAIL_KEY)
  return v === null ? true : v === 'true'
}

export function setEmailNotificationsEnabled(enabled: boolean) {
  localStorage.setItem(EMAIL_KEY, String(enabled))
}

export function getInAppNotificationsEnabled(): boolean {
  const v = localStorage.getItem(IN_APP_KEY)
  return v === null ? true : v === 'true'
}

export function setInAppNotificationsEnabled(enabled: boolean) {
  localStorage.setItem(IN_APP_KEY, String(enabled))
}
