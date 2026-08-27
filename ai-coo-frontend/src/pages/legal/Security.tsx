import { Link } from 'react-router-dom'
import LegalPageLayout from './LegalPageLayout'
import LegalSection from './LegalSection'

const LAST_UPDATED = 'August 27, 2026'

export default function Security() {
  return (
    <LegalPageLayout title="Security" lastUpdated={LAST_UPDATED}>
      <LegalSection number="1" title="Authorization">
        <p>
          Access to GitHub, Gmail, and Google Calendar is granted through each provider's own OAuth
          consent screen — WorkForge never asks for or stores your Google or GitHub password. You can see
          exactly which permissions are being requested before approving, and can revoke access at any
          time from your Integrations settings or directly from your Google Account permissions page.
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
          All communication between your browser, our backend, and Google/GitHub's APIs uses HTTPS/TLS.
        </p>
      </LegalSection>

      <LegalSection number="4" title="Organization Isolation">
        <p>
          WorkForge supports multiple organizations. Every stored token is tied to a specific
          organization's integration record, and every API call resolves its access token from that
          record — one organization's request can never be served using another organization's stored
          credentials.
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
          Disconnecting an integration immediately and permanently deletes its stored OAuth token.
          Deleting your account permanently removes your organization's data, including all stored tokens.
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
          See our <Link to="/privacy" className="text-[var(--color-signal)] hover:brightness-110">Privacy Policy</Link> for what Google user data we access and why.
        </p>
      </LegalSection>
    </LegalPageLayout>
  )
}
