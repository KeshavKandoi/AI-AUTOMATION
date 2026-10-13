import LegalPageLayout from './LegalPageLayout'
import LegalSection from './LegalSection'

const LAST_UPDATED = 'October 13, 2026'

export default function PrivacyPolicy() {
  return (
    <LegalPageLayout title="Privacy Policy" lastUpdated={LAST_UPDATED}>
      <LegalSection number="1" title="Information WorkForge handles">
        <p>
          WorkForge stores account and organization details, tasks, workflows, scheduled jobs,
          integration settings, and audit records in its application database. WorkForge does not
          read Gmail messages or the Gmail inbox. When Gmail is connected, WorkForge requests the
          connected Google account email address and permission to send email. When Calendar is
          connected, WorkForge accesses calendar events and event details needed for the features
          you use.
        </p>
        <p>
          The Gmail connection requests the{' '}
          <code className="break-all">https://www.googleapis.com/auth/gmail.send</code> and{' '}
          <code className="break-all">https://www.googleapis.com/auth/userinfo.email</code>{' '}scopes. Calendar requests{' '}
          <code className="break-all">https://www.googleapis.com/auth/calendar</code>. WorkForge calls Gmail&apos;s send
          API and Google&apos;s user-info endpoint; it does not list, retrieve, or search inbox
          messages. Calendar access is used to list upcoming events and create events you request
          or approve.
        </p>
      </LegalSection>

      <LegalSection number="2" title="How Google data is used and shared">
        <p>
          WorkForge uses the Google account email address to identify the connected account and,
          when no separate recipient is configured, as the default recipient for workflow email.
          WorkForge sends messages you configure or approve through Gmail. Google and the message
          recipients receive the message address, subject, and body so Google can deliver it.
          WorkForge does not read messages from the inbox.
        </p>
        <p>
          WorkForge fetches upcoming Calendar events to display them, summarize what is coming up,
          and check for overlapping times or scheduling conflicts. It may create a Calendar event
          using the title, time, and other details you request or approve. The event is created in
          your Google Calendar and is subject to Google&apos;s handling of that account.
        </p>
        <p>
          When you request a Calendar summary and upcoming events are available, WorkForge sends up
          to 10 event titles and their start and end dates or times to an external AI service
          provider. It also sends instructions to count events, identify overlapping times, and
          describe what is coming up soonest. The provider returns a summary to WorkForge, which
          returns it to you. WorkForge does not store the prompt or generated summary in its
          application database. WorkForge&apos;s code does not determine whether the external provider
          retains prompts or uses them to improve or train models; that depends on the production
          provider configuration and terms, which must be checked before making a provider-wide
          no-training statement.
        </p>
        <p>
          Google provides Gmail and Calendar services. An external AI service provider processes
          Calendar summary prompts when you request that feature. Supabase provides account
          authentication, database, and storage services for WorkForge. WorkForge does not sell
          Google user data or use it for advertising.
        </p>
      </LegalSection>

      <LegalSection number="3" title="Storage and retention">
        <p>
          WorkForge does not apply a general automatic expiration period to account, task, workflow,
          sent-message, or audit records. These records remain while the account or organization is
          active and until they are deleted through the available controls or by an approved deletion
          request. Hosting and database backups may follow the provider&apos;s separate retention
          settings.
        </p>
        <ul className="list-disc pl-6">
          <li>
            <strong>Google account email:</strong> WorkForge requests it from Google when resolving
            the connected Gmail account. It is not stored as a separate Google profile field. If
            used as a recipient, the address can be stored in a scheduled email job or send/audit
            metadata until those records are deleted.
          </li>
          <li>
            <strong>OAuth credentials:</strong> Gmail and Calendar access and refresh tokens are
            encrypted before storage in the WorkForge database. They are retained while the
            integration remains connected; access-token expiry does not remove a refresh token.
            Disconnecting the integration deletes its stored token records.
          </li>
          <li>
            <strong>Calendar data and summaries:</strong> upcoming event details and generated
            summaries are processed to serve the request and are not saved in WorkForge&apos;s
            application database by the listing and summary endpoints. Calendar automation stores
            the block settings you configure and run records, including dates, status, and an event
            ID when it creates an event. Events created by WorkForge remain in Google Calendar until
            you remove them there.
          </li>
          <li>
            <strong>Sent-message and audit metadata:</strong> WorkForge stores configured scheduled
            email content while the job exists, and may store recipients, Gmail message IDs, workflow
            trigger context, task details, and action results in job runs and audit records. It does
            not store the Gmail message body as a sent-message archive. These records have no
            automatic WorkForge expiry period.
          </li>
          <li>
            <strong>Tasks and other organization records:</strong> task, workflow, and related
            organization data remain until deleted by the organization or through account deletion
            when the account is the organization&apos;s only member. Shared organization data remains
            for the other members.
          </li>
        </ul>
        <p>
          WorkForge does not control or set the external AI service provider&apos;s prompt retention
          or model-improvement practices. Those practices depend on the provider and production
          account configuration. WorkForge cannot confirm from this application&apos;s code how long
          the provider retains prompts or whether the provider uses them for generalized model
          improvement. Check the deployed provider account&apos;s data-handling terms and settings
          before relying on a no-training representation. This does not change WorkForge&apos;s own
          retention rule: the Calendar prompt and generated summary are not stored in WorkForge&apos;s
          application database. Calendar integration credentials and Calendar automation settings
          and run records follow the WorkForge retention and deletion rules above.
        </p>
      </LegalSection>

      <LegalSection number="4" title="Disconnecting integrations and deleting data">
        <p>
          Disconnecting Gmail or Calendar in WorkForge deletes the stored OAuth tokens and marks
          that integration disconnected. It does not delete past tasks, sent-message metadata,
          audit records, scheduled-job history, or events already created in Google Calendar. A
          WorkForge disconnect also does not revoke Google&apos;s account-level grant. To revoke that
          grant, remove WorkForge from your Google Account&apos;s third-party access settings as
          well.
        </p>
        <p>
          You can start account deletion in Settings and confirm with your password. WorkForge
          removes the account profile, authentication account, and verification codes. If you are
          the only member of the organization, deletion also removes its organization data,
          integrations, and stored OAuth credentials. If other members remain, shared tasks,
          workflows, integrations, and history are kept for them; audit entries are retained with
          your user attribution removed. If the deletion process reports an error, some records may
          already have been removed, so contact support at{' '}
          <a className="text-[var(--color-signal)] underline" href="mailto:testerappp2001@gmail.com">
            testerappp2001@gmail.com
          </a>{' '}
          to request help completing or reviewing the deletion. You can also request deletion at
          that address.
        </p>
      </LegalSection>

      <LegalSection number="5" title="Security and operational logs">
        <p>
          OAuth tokens are encrypted before they are stored. Access is limited by organization in
          application logic. WorkForge records operational and audit information such as action
          outcomes, recipients, message IDs, task or workflow context, and error details. Workflow
          context may include task titles, commit messages, or issue text. WorkForge&apos;s application
          code does not deliberately log passwords or raw OAuth credentials. Runtime log retention
          is governed by the hosting provider&apos;s settings and may differ from WorkForge database
          retention.
        </p>
      </LegalSection>

      <LegalSection number="6" title="Questions and Google controls">
        <p>
          You can disconnect an integration in WorkForge, delete your account in Settings, or
          contact us at{' '}
          <a className="text-[var(--color-signal)] underline" href="mailto:testerappp2001@gmail.com">
            testerappp2001@gmail.com
          </a>
          . You can manage or revoke WorkForge&apos;s access in your{' '}
          <a
            className="text-[var(--color-signal)] underline"
            href="https://myaccount.google.com/permissions"
            target="_blank"
            rel="noreferrer"
          >
            Google Account permissions
          </a>
          . Revoking access at Google may cause connected WorkForge features to stop working until
          you reconnect.
        </p>
      </LegalSection>
    </LegalPageLayout>
  )
}
