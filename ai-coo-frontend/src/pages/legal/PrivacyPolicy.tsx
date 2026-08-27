import { Link } from 'react-router-dom'
import LegalPageLayout from './LegalPageLayout'
import LegalSection from './LegalSection'

const CONTACT_EMAIL = 'testerappp2001@gmail.com'
const LAST_UPDATED = 'August 28, 2026'

export default function PrivacyPolicy() {
  return (
    <LegalPageLayout title="Privacy Policy" lastUpdated={LAST_UPDATED}>
      <LegalSection number="1" title="Introduction">
        <p>
          WorkForge ("we", "our", "the service") is a workflow automation platform. This Privacy Policy
          explains what information we collect, including Google user data accessed through Gmail and
          Google Calendar integrations, how it is used, how it is stored and protected, who it is shared
          with, and the choices you have about it. As explained throughout this policy, Google user data
          is accessed and used solely to provide or improve the specific, user-facing WorkForge features
          described below — never for any unrelated purpose.
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
          integration, and each permission below exists solely to provide a specific, named WorkForge
          feature. We do not access your Google Contacts, Drive files, or any other Google data not listed
          here, and we do not access any Google data for a purpose not described below.
        </p>
        <p className="text-[var(--color-text-primary)] font-medium mt-2">Gmail</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>
            <strong>Job Hunter:</strong> scans recent messages (up to the last 14 days, up to 50 messages
            per scan), reading message headers, full body content, and attachment metadata, to detect
            recruitment-related emails (interview invitations, assessments, offers, rejections,
            rescheduling) and keep your job-application tracker up to date. Full message body access is
            required for this feature because classification depends on the wording of the email body, not
            just its subject line.
          </li>
          <li>
            <strong>AI planner:</strong> reads the sender, subject, and short snippet of your unread
            messages to suggest tasks for your approval.
          </li>
          <li>
            <strong>Gmail unread mail view:</strong> the Gmail page in WorkForge displays your unread
            messages (sender, subject, snippet) directly in the app so you can see them at a glance. This
            view does not involve any AI processing.
          </li>
          <li>
            <strong>Gmail AI summary:</strong> when you click "Load AI summary" on the Gmail page, WorkForge
            sends the same limited data (sender, subject, and snippet of your unread messages) to Google
            Gemini to generate a short natural-language summary, described further in Section 5.
          </li>
          <li>
            <strong>Sending email</strong> — used only to provide the workflow-automation feature, when you
            configure a workflow action to send an email (for example, "GitHub push → send an email"), or
            when you explicitly approve a task that sends an email. WorkForge never sends email on its own
            initiative.
          </li>
          <li>
            <strong>Your Google account email address</strong> — used solely to identify your account
            during sign-in to the Google integration.
          </li>
        </ul>
        <p className="text-[var(--color-text-primary)] font-medium mt-2">Google Calendar</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>
            <strong>Job Hunter interview events:</strong> creates a calendar event when an interview
            invitation is detected in your Gmail, and updates or cancels that event if a reschedule or
            withdrawal email is later detected.
          </li>
          <li>
            <strong>Workflow automation:</strong> creates events as part of workflows you configure.
          </li>
          <li>
            <strong>Lunch block:</strong> if you enable it, automatically creates one daily event at times
            you set.
          </li>
          <li>
            <strong>AI planner:</strong> reads the title and start time of your next few upcoming events to
            factor them into suggested tasks.
          </li>
          <li>
            <strong>Calendar page:</strong> displays your upcoming events, and lets you manually create a
            new event directly in WorkForge.
          </li>
          <li>
            <strong>Calendar AI summary:</strong> when you click "Load AI summary" on the Calendar page,
            WorkForge sends limited event information (event title/summary and start/end time) to Google
            Gemini to generate a short natural-language summary, described further in Section 5.
          </li>
        </ul>
        <p>
          All Calendar operations described above act on individual calendar events only. WorkForge does
          not read or modify your calendar list, calendar sharing settings, or any calendar other than your
          primary calendar.
        </p>
      </LegalSection>

      <LegalSection number="4" title="How Google User Data Is Used">
        <p>
          Google user data is used solely to provide the specific, user-facing WorkForge features you have
          enabled or configured — never for any purpose beyond delivering these features. Concretely:
        </p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li><strong>Job Hunter:</strong> Gmail data → automatically detect application status changes → update your tracked applications and, where an interview is detected, create/update/cancel the corresponding Calendar event.</li>
          <li><strong>Workflow automation:</strong> a GitHub event you configure (push, issue, or pull request) → a Gmail send-email action and/or a Calendar create-event action you configured for that workflow.</li>
          <li><strong>Lunch block:</strong> a daily schedule you configure → WorkForge checks and, if needed, creates one Calendar event for that window.</li>
          <li><strong>AI planner:</strong> your unread email metadata and upcoming calendar events → a suggested task list you review and approve before anything happens.</li>
          <li><strong>Gmail unread mail view / Calendar page:</strong> your unread messages or upcoming events → displayed directly to you in WorkForge, so you can see them without leaving the app.</li>
          <li><strong>Gmail AI summary / Calendar AI summary:</strong> the same limited data shown above → a short natural-language summary generated on your explicit request and shown only to you.</li>
        </ul>
        <p>
          WorkForge never independently decides to send an email or create a calendar event outside of
          these user-configured or user-initiated features, and Google user data is never repurposed beyond
          providing or improving the features listed above.
        </p>
      </LegalSection>

      <LegalSection number="5" title="AI Processing of Google User Data">
        <p>
          WorkForge uses Google's Gemini API solely as a service provider to help deliver specific,
          user-facing WorkForge features. Only the specific Google data described below — and nothing else
          — is sent to Gemini, strictly to generate the outputs those features require:
        </p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>
            <strong>Interview date/time extraction (part of Job Hunter):</strong> when Job Hunter detects an
            interview-related email, it first looks for a structured calendar invite (a .ics attachment or
            calendar MIME part) in that email. Only if no structured invite is found does it send the
            email's subject and a portion of its body (up to roughly 3,000 characters) to Gemini, solely to
            extract a likely interview date and time. A low-confidence or unparseable result is discarded
            and no calendar event is created from it.
          </li>
          <li>
            <strong>AI planner task suggestions:</strong> the sender, subject, and short snippet of your
            unread Gmail messages, and the title/time of your upcoming Calendar events, are sent to Gemini
            solely to generate suggested task titles and priorities for your review.
          </li>
          <li>
            <strong>Gmail AI summary:</strong> when you explicitly request it, only the sender, subject, and
            short snippet of your unread messages are sent to Gemini to generate the requested summary.
          </li>
          <li>
            <strong>Calendar AI summary:</strong> when you explicitly request it, only the title/summary and
            start/end time of your upcoming events are sent to Gemini to generate the requested summary.
          </li>
        </ul>
        <p>
          Gemini processes this data only to produce the specific, immediate output described above for the
          corresponding feature, and each response is returned to you and is not used for any other
          purpose. Google user data sent to Gemini is not used to train any general-purpose AI/ML model,
          and is not used for any research or model-improvement purpose unrelated to generating these
          feature outputs.
        </p>
      </LegalSection>

      <LegalSection number="6" title="Purpose Limitation">
        <p>Google user data is used only to provide or improve the specific, user-facing WorkForge features described in this policy. Specifically:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>Google user data is never used for advertising or targeted advertising.</li>
          <li>Google user data is never sold.</li>
          <li>Google user data is never used for unrelated profiling, creditworthiness, or lending decisions.</li>
          <li>Google user data is never used to train generalized or foundational AI models.</li>
          <li>Google user data is never used for any purpose outside the functionality explicitly described in this Privacy Policy.</li>
        </ul>
      </LegalSection>

      <LegalSection number="7" title="Google API Services User Data Policy">
        <p>
          WorkForge's use and transfer of information received from Google APIs complies with the <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer" className="text-[var(--color-signal)] hover:brightness-110">Google API Services User Data Policy</a>, including its Limited Use requirements. Google user data is accessed and used only to
          provide or improve the user-facing features described in this Privacy Policy. We do not use
          Google user data for advertising, targeted advertising, selling data, creditworthiness or lending
          purposes, or any unrelated purpose. We do not sell Google user data. We do not transfer Google
          user data to third parties except where necessary to provide or improve a user-facing WorkForge
          feature, as described in this Privacy Policy. Any service provider processing Google user data on
          WorkForge's behalf is permitted to process that data only for the purposes necessary to provide or
          improve the relevant WorkForge feature and is subject to appropriate contractual and security
          obligations.
        </p>
      </LegalSection>

      <LegalSection number="8" title="Data Sharing and Disclosure">
        <p>
          We do not sell Google user data or share it with advertisers, data brokers, or unrelated third
          parties. Google user data is transmitted only as necessary to provide or improve the specific
          WorkForge feature you use, and only to the following:
        </p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li><span className="text-[var(--color-text-primary)]">Google's own APIs</span> — used to access or act on your Google account: Gmail and Calendar API calls are made directly to Google to read or act on your account, as described in Section 3.</li>
          <li><span className="text-[var(--color-text-primary)]">Google Gemini API</span> — receives only the specific Google data described in Section 5, solely to generate the outputs required for the AI-powered features described there.</li>
          <li><span className="text-[var(--color-text-primary)]">Supabase</span> — our database provider, which stores encrypted OAuth tokens and limited Gmail metadata (sender, subject, and attachment names — not full message bodies) needed to avoid reprocessing the same email twice, solely to support the features described above.</li>
        </ul>
        <p>
          Each of these is used only as necessary to provide or improve the corresponding WorkForge
          functionality. Discord notifications (where you configure them) contain only the title/content of
          the GitHub event that triggered the workflow — never Gmail or Calendar content.
        </p>
      </LegalSection>

      <LegalSection number="9" title="Data Storage and Security">
        <p>
          OAuth access tokens and refresh tokens for Google and GitHub are encrypted at rest (Fernet
          symmetric encryption) before being stored in our Supabase/PostgreSQL database, and are decrypted
          only in-memory at the moment they're used to call an API on your behalf. All communication with
          our backend and with Google/GitHub APIs uses HTTPS/TLS. Access tokens are resolved per
          organization/integration — a request for one organization's data cannot use another
          organization's stored token. GitHub webhook deliveries are verified using a per-organization
          HMAC signature before any workflow is triggered; a delivery that doesn't match a stored secret is
          rejected. We do not currently hold SOC 2, ISO 27001, or similar independent security
          certifications, and we have not undergone independent third-party penetration testing.
        </p>
      </LegalSection>

      <LegalSection number="10" title="Data Retention">
        <p>
          Google user data and OAuth tokens are retained only while the corresponding integration remains
          connected. Job Hunter records (application status, detected Gmail event metadata, matched
          calendar events) are retained while your account is active, to keep your tracker functional. AI
          summary responses (Gmail and Calendar) are returned to you at request time and are not separately
          stored.
        </p>
      </LegalSection>

      <LegalSection number="11" title="Data Deletion and Revocation">
        <p>You can remove Google access and data at any time:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li><strong>Disconnect an integration:</strong> from your Integrations settings, disconnecting Gmail or Calendar immediately and permanently deletes the corresponding stored OAuth token from our database.</li>
          <li><strong>Revoke at the source:</strong> you can also revoke WorkForge's access directly from your Google Account permissions page at any time.</li>
          <li><strong>Delete your account:</strong> from Settings, account deletion permanently removes your organization's data — including all stored OAuth tokens, workflow configurations, Job Hunter records, tasks, and audit logs — and deletes your login credentials.</li>
        </ul>
      </LegalSection>

      <LegalSection number="12" title="User Control and Consent">
        <p>
          You choose which integrations to connect and which workflows to create. Google authorization
          happens through Google's own OAuth consent screen, which shows you exactly what access is being
          requested before you approve it. Nothing is accessed until you complete that consent flow.
        </p>
      </LegalSection>

      <LegalSection number="13" title="Children's Privacy">
        <p>
          WorkForge is not directed to, and is not intended for use by, children. We do not knowingly
          collect personal information from children.
        </p>
      </LegalSection>

      <LegalSection number="14" title="Changes to This Privacy Policy">
        <p>
          We may update this Privacy Policy as our data practices change. Material changes will be
          reflected by an updated "Last updated" date above; if we make a change we consider significant,
          we will make reasonable efforts to notify active users.
        </p>
      </LegalSection>

      <LegalSection number="15" title="Contact">
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
