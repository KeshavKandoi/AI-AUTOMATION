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
          For a Calendar summary, WorkForge sends the event titles and start and end times returned
          by Calendar to Google Gemini, along with instructions to count events, identify overlaps,
          and describe what is coming up soonest. The summary is returned to you. WorkForge itself
          does not use Google Workspace data to develop, improve, or train generalized or
          non-personalized AI/ML models. This describes WorkForge&apos;s use; Google&apos;s separate
          handling of Gemini prompts depends on the API service tier described below. WorkForge
          does not persist the Calendar summary in its application database.
        </p>
        <p>
          Google provides Gmail, Calendar, and Gemini processing. Supabase provides account
          authentication, database, and storage services for WorkForge. WorkForge does not sell
          Google user data or use it for advertising. Google&apos;s handling of Gemini prompts
          depends on the Gemini API service tier used by WorkForge; see the retention and AI
          details below.
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
          WorkForge&apos;s Calendar summary feature uses the Gemini Developer API. Google states that
          for Paid Services, prompts and responses are not used to improve Google products, although
          they may be logged for a limited period for abuse monitoring. For Unpaid Services, Google
          states that submitted content and responses may be used to provide, improve, and develop
          Google products and machine-learning technologies. WorkForge&apos;s code cannot determine
          whether its deployed Gemini project has active billing, so WorkForge cannot promise that
          Google will not use these prompts for product or model improvement unless the deployment
          is confirmed to use Paid Services. Google&apos;s{' '}
          <a
            className="text-[var(--color-signal)] underline"
            href="https://ai.google.dev/gemini-api/terms"
            target="_blank"
            rel="noreferrer"
          >
            Gemini API terms
          </a>{' '}
          and{' '}
          <a
            className="text-[var(--color-signal)] underline"
            href="https://ai.google.dev/gemini-api/docs/zdr"
            target="_blank"
            rel="noreferrer"
          >
            Gemini retention documentation
          </a>{' '}
          describe the current handling. Google does not give a single fixed retention period for
          prompts submitted under Unpaid Services.
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
