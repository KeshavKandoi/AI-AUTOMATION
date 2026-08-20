const EMAIL_KEY = 'ai-coo-pref-email-notifications'
const IN_APP_KEY = 'ai-coo-pref-in-app-notifications'

/** Device-local notification preferences. No backend table exists for
 * these yet — they only affect this browser/device. Email notifications
 * has no in-app hook to gate (would require backend delivery-channel
 * awareness); in-app does gate the sidebar unread badge, since that's a
 * purely client-side rendering decision. */
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
