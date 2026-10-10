import LegalPageLayout from './LegalPageLayout'
import LegalSection from './LegalSection'

const LAST_UPDATED = 'October 11, 2026'

export default function PrivacyPolicy() {
  return (
    <LegalPageLayout title="Privacy Policy" lastUpdated={LAST_UPDATED}>
      <LegalSection number="1" title="Information we collect">
        <p>WorkForge stores your account name, email address, organization, tasks, workflow settings, job applications, scheduled jobs, and audit records. Basic request logs help us operate and secure the service.</p>
      </LegalSection>
      <LegalSection number="2" title="Google account access">
        <p>Connecting Gmail is optional. We request only the Gmail send permission and your Google account email address. WorkForge sends email when you approve a task or configure a workflow or scheduled email job. It does not read your inbox, list messages, or modify mailbox state.</p>
      </LegalSection>
      <LegalSection number="3" title="Use and sharing">
        <p>We use your data to provide the features you request. Gmail messages you choose to send go to Google and their recipients. GitHub activity and task context may be sent to Google Gemini to generate suggestions. We do not sell Google user data or use it for advertising.</p>
      </LegalSection>
      <LegalSection number="4" title="Storage and choices">
        <p>OAuth tokens are encrypted before storage and tied to your organization. You can disconnect an integration to delete its tokens or delete your account and organization data from Settings. You can also revoke access in your Google Account.</p>
      </LegalSection>
    </LegalPageLayout>
  )
}
