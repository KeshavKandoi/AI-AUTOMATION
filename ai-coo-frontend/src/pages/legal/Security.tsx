import { Link } from 'react-router-dom'
import LegalPageLayout from './LegalPageLayout'
import LegalSection from './LegalSection'

const LAST_UPDATED = 'October 13, 2026'

export default function Security() {
  return (
    <LegalPageLayout title="Security" lastUpdated={LAST_UPDATED}>
      <LegalSection number="1" title="Authorization">
        <p>
          Access to GitHub, Gmail, and Google Calendar is granted through each provider&apos;s OAuth
          consent screen. WorkForge does not ask for or store your Google or GitHub password. You
          can review the permissions before approving. Disconnecting Gmail or Calendar in WorkForge
          deletes the integration&apos;s stored OAuth tokens and marks it disconnected, but does not
          revoke the grant in your Google Account. To revoke that grant, remove WorkForge from your
          Google Account permissions.
        </p>
      </LegalSection>

      <LegalSection number="2" title="Credential Storage">
        <p>
          OAuth access tokens and refresh tokens are encrypted at rest using Fernet symmetric encryption
          before being written to our database, and are only decrypted in-memory at the moment they're
          needed to make an API call on your behalf.
        </p>
      </LegalSection>

      <LegalSection number="3" title="Encryption in Transit">
        <p>
          WorkForge calls Google and GitHub API endpoints over HTTPS. Production deployments should
          serve the browser and backend over HTTPS; local development may use HTTP.
        </p>
      </LegalSection>

      <LegalSection number="4" title="Organization Isolation">
        <p>
          WorkForge supports multiple organizations. Stored tokens are tied to an organization&apos;s
          integration record, and backend integration routes resolve credentials using the
          authenticated organization context. The server performs organization ownership checks
          before using those credentials.
        </p>
      </LegalSection>

      <LegalSection number="5" title="Webhook Verification">
        <p>
          GitHub webhook deliveries are authenticated using a per-organization HMAC-SHA256 signature.
          A delivery is only processed for the organization whose stored secret verifies it; deliveries
          that don't match a valid signature are rejected.
        </p>
      </LegalSection>

      <LegalSection number="6" title="Data Deletion">
        <p>
          Disconnecting Gmail or Calendar deletes the selected integration&apos;s stored OAuth token
          records and marks that integration disconnected. It does not remove messages already sent,
          events already created in Google Calendar, historical WorkForge records, or Google&apos;s
          account-level access grant. Revoke that grant separately in Google Account permissions.
        </p>
        <p>
          Account deletion requires password confirmation. When the account is the organization&apos;s
          only member, WorkForge deletes the organization-scoped records, integration records, and
          OAuth tokens before deleting the organization and authentication account. When other
          members remain, WorkForge removes the departing account profile and authentication
          account, retains shared organization records and integration credentials for the other
          members, and removes that user&apos;s identifier from audit records. The deletion process
          stops and reports an error if a cleanup step fails; some records may already have been
          removed. Database backups may follow separate provider retention settings.
        </p>
      </LegalSection>

      <LegalSection number="7" title="What We Don't Claim">
        <p>
          We do not currently hold SOC 2, ISO 27001, or other independent security certifications, and we
          have not undergone an independent third-party penetration test. This page describes the actual
          controls implemented today.
        </p>
      </LegalSection>

      <LegalSection number="8" title="Related Reading">
        <p>
          See our <Link to="/privacy" className="text-signal hover:brightness-110">Privacy Policy</Link> for Google data use, retention, and deletion details, and our <Link to="/terms" className="text-signal hover:brightness-110">Terms of Service</Link> for the terms that apply to connected services.
        </p>
      </LegalSection>
    </LegalPageLayout>
  )
}
