import { Link } from 'react-router-dom'
import LegalPageLayout from './LegalPageLayout'
import LegalSection from './LegalSection'

const CONTACT_EMAIL = 'testerappp2001@gmail.com'
const LAST_UPDATED = 'August 27, 2026'

export default function PrivacyPolicy() {
  return (
    <LegalPageLayout title="Privacy Policy" lastUpdated={LAST_UPDATED}>
      <LegalSection number="1" title="Introduction">
        <p>
          WorkForge ("we", "our", "the service") is a workflow automation platform. This Privacy Policy
          explains what information we collect, including Google user data accessed through Gmail and
          Google Calendar integrations, how it is used, how it is stored and protected, who it is shared
          with, and the choices you have about it.
        </p>
      </LegalSection>

      <LegalSection number="2" title="Information We Collect">
        <p>We collect the following categories of information:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>Account information: your name, email address, and organization name.</li>
          <li>Authentication information used to sign you in and keep your account secure.</li>
          <li>Information you provide while using WorkForge: tasks, workflow configurations, job-application records, and scheduled jobs.</li>
          <li>Technical information such as basic request logs, needed to operate and secure the service.</li>
          <li>Google user data, described in detail in Section 3, accessed only after you connect a Google integration.</li>
        </ul>
      </LegalSection>

      <LegalSection number="3" title="Google User Data We Access">
        <p>
          You may optionally connect your Google account to enable Gmail and/or Google Calendar
          integrations. We only request Google permissions when you explicitly choose to connect a Google
          integration, and each permission below exists to support a specific feature. We do not access
          your Google Contacts, Drive files, or any other Google data not listed here.
        </p>
        <p className="text-[var(--color-text-primary)] font-medium mt-2">Gmail</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>
            <strong>Reading your inbox</strong> — WorkForge scans recent messages (up to the last 14 days,
            up to 50 messages per scan) in two features: (1) <em>Job Hunter</em>, which detects
            recruitment-related emails (interview invitations, assessments, offers, rejections, rescheduling)
            to keep your job-application tracker up to date; and (2) the <em>AI planner</em>, which reads the
            sender, subject, and short snippet of your unread messages to suggest tasks for your approval.
            We do not read Gmail messages for any purpose outside these two features.
          </li>
          <li>
            <strong>Sending email</strong> — used only when you configure a workflow action to send an
            email (for example, "GitHub push → send an email"). WorkForge never sends email on its own
            initiative; it only sends what a workflow you configured specifies.
          </li>
          <li>
            <strong>Your Google account email address</strong> — used to identify your account during
            sign-in to the Google integration.
          </li>
        </ul>
        <p className="text-[var(--color-text-primary)] font-medium mt-2">Google Calendar</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>
            <strong>Creating, reading, and updating calendar events</strong> — used to: create an interview
            event when Job Hunter detects an interview invitation in your Gmail (and update or cancel that
            event if a reschedule or withdrawal email is later detected); create events as part of workflows
            you configure; and, if you enable it, automatically create a daily "lunch block" event at times
            you set. The AI planner also reads your next few upcoming events (title and start time) to
            factor them into suggested tasks.
          </li>
        </ul>
      </LegalSection>

      <LegalSection number="4" title="How Google User Data Is Used">
        <p>Concretely, here is how each feature uses Google user data:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li><strong>Job Hunter:</strong> Gmail → automatically detect application status changes → update your tracked applications and, where an interview is detected, create/update/cancel the corresponding Calendar event.</li>
          <li><strong>Workflow automation:</strong> a GitHub event you configure (push, issue, or pull request) → a Gmail send-email action and/or a Calendar create-event action you configured for that workflow.</li>
          <li><strong>Lunch block:</strong> a daily schedule you configure → WorkForge checks and, if needed, creates one Calendar event for that window.</li>
          <li><strong>AI planner:</strong> your unread email metadata and upcoming calendar events → a suggested task list you review and approve before anything happens.</li>
        </ul>
        <p>
          WorkForge never independently decides to send an email or create a calendar event outside of
          these user-configured features.
        </p>
      </LegalSection>

      <LegalSection number="5" title="AI Processing of Google User Data">
        <p>
          WorkForge uses Google's Gemini API to power two specific features, described here for
          transparency:
        </p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>
            <strong>Interview date/time extraction:</strong> when Job Hunter detects an interview-related
            email, it first looks for a structured calendar invite (a .ics attachment or calendar MIME
            part) in that email. Only if no structured invite is found does it send the email's subject and
            a portion of its body (up to roughly 3,000 characters) to Gemini to extract a likely date and
            time. A low-confidence or unparseable result is discarded and no calendar event is created from it.
          </li>
          <li>
            <strong>AI planner task suggestions:</strong> the sender, subject, and short snippet of your
            unread Gmail messages, and the title/time of your upcoming Calendar events, are included in a
            prompt sent to Gemini to generate suggested task titles and priorities for your review.
          </li>
        </ul>
        <p>
          Google user data is not used to train any general-purpose AI/ML model. It is processed solely to
          generate the specific outputs described above.
        </p>
      </LegalSection>

      <LegalSection number="6" title="Purpose Limitation">
        <p>
          Google user data is used only to provide the WorkForge functionality described in this policy
          that you have explicitly enabled or configured. We do not sell Google user data. We do not use
          Google user data for advertising or targeted advertising. We do not use it for credit
          decisions, unrelated profiling, or any purpose outside the features described above.
        </p>
      </LegalSection>

      <LegalSection number="7" title="Data Sharing and Disclosure">
        <p>We do not sell Google user data or share it with advertisers or data brokers. Google user data is transmitted only where necessary to provide a feature you use:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li><span className="text-[var(--color-text-primary)]">Google's own APIs</span> — Gmail and Calendar API calls are made directly to Google to read or act on your account, as described above.</li>
          <li><span className="text-[var(--color-text-primary)]">Google Gemini API</span> — receives the specific email/calendar content described in Section 5, solely to generate the outputs described there.</li>
          <li><span className="text-[var(--color-text-primary)]">Supabase</span> — our database provider stores encrypted OAuth tokens and limited Gmail metadata (sender, subject, and attachment names — not full message bodies) needed to avoid reprocessing the same email twice.</li>
        </ul>
        <p>
          Discord notifications (where you configure them) contain only the title/content of the GitHub
          event that triggered the workflow — never Gmail or Calendar content.
        </p>
      </LegalSection>

      <LegalSection number="8" title="Data Storage and Security">
        <p>
          OAuth access tokens and refresh tokens for Google and GitHub are encrypted at rest (Fernet
          symmetric encryption) before being stored in our Supabase/PostgreSQL database, and are decrypted
          only in-memory at the moment they're used to call an API on your behalf. All communication with
          our backend and with Google/GitHub APIs uses HTTPS/TLS. Access tokens are resolved per
          organization/integration — a request for one organization's data cannot use another
          organization's stored token. GitHub webhook deliveries are verified using a per-organization
          HMAC signature before any workflow is triggered; a delivery that doesn't match a stored secret is
          rejected. We do not currently hold SOC 2, ISO 27001, or similar independent security
          certifications.
        </p>
      </LegalSection>

      <LegalSection number="9" title="Data Retention">
        <p>
          Google user data and OAuth tokens are retained only while the corresponding integration remains
          connected. Job Hunter records (application status, detected Gmail event metadata, matched
          calendar events) are retained while your account is active, to keep your tracker functional.
        </p>
      </LegalSection>

      <LegalSection number="10" title="Data Deletion and Revocation">
        <p>You can remove Google access and data at any time:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li><strong>Disconnect an integration:</strong> from your Integrations settings, disconnecting Gmail or Calendar immediately and permanently deletes the corresponding stored OAuth token from our database.</li>
          <li><strong>Revoke at the source:</strong> you can also revoke WorkForge's access directly from your Google Account permissions page at any time.</li>
          <li><strong>Delete your account:</strong> from Settings, account deletion permanently removes your organization's data — including all stored OAuth tokens, workflow configurations, Job Hunter records, tasks, and audit logs — and deletes your login credentials.</li>
        </ul>
      </LegalSection>

      <LegalSection number="11" title="User Control and Consent">
        <p>
          You choose which integrations to connect and which workflows to create. Google authorization
          happens through Google's own OAuth consent screen, which shows you exactly what access is being
          requested before you approve it. Nothing is accessed until you complete that consent flow.
        </p>
      </LegalSection>

      <LegalSection number="12" title="Children's Privacy">
        <p>
          WorkForge is not directed to, and is not intended for use by, children. We do not knowingly
          collect personal information from children.
        </p>
      </LegalSection>

      <LegalSection number="13" title="Changes to This Privacy Policy">
        <p>
          We may update this Privacy Policy as our data practices change. Material changes will be
          reflected by an updated "Last updated" date above; if we make a change we consider significant,
          we will make reasonable efforts to notify active users.
        </p>
      </LegalSection>

      <LegalSection number="14" title="Contact">
        <p>
          Questions about this Privacy Policy or how your Google user data is handled? Contact us at{' '}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-[var(--color-signal)] hover:brightness-110">
            {CONTACT_EMAIL}
          </a>. See also our <Link to="/security" className="text-[var(--color-signal)] hover:brightness-110">Security</Link> page.
        </p>
      </LegalSection>
    </LegalPageLayout>
  )
}
