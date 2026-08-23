import LegalPageLayout from './LegalPageLayout'
import LegalSection from './LegalSection'

const CONTACT_EMAIL = 'testerappp2001@gmail.com'
const LAST_UPDATED = 'August 23, 2026'

export default function PrivacyPolicy() {
  return (
    <LegalPageLayout title="Privacy Policy" lastUpdated={LAST_UPDATED}>
      <LegalSection number="1" title="Introduction">
        <p>
          WorkForge ("we", "our", "the service") respects your privacy. This Privacy Policy explains what
          information we collect when you use WorkForge, how we use it, how it is stored, and the choices
          you have about it.
        </p>
      </LegalSection>

      <LegalSection number="2" title="Information We Collect">
        <p>We collect the following categories of information:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>Account information: your name, email address, and organization name.</li>
          <li>Authentication information used to sign you in and keep your account secure.</li>
          <li>Information you provide while using WorkForge, such as tasks, workflow configurations, and scheduled jobs.</li>
          <li>Technical information such as basic request logs, needed to operate and secure the service.</li>
        </ul>
      </LegalSection>

      <LegalSection number="3" title="Google Account and OAuth Data">
        <p>
          You may optionally connect your Google account to WorkForge to enable specific integrations,
          currently Gmail and Google Calendar. We only request access to these services when you explicitly
          choose to connect them, and only to provide the corresponding feature inside WorkForge (for
          example, reading unread email summaries or creating calendar events you request).
        </p>
        <p>
          We do not access your Gmail or Google Calendar data except through the specific, user-initiated
          actions described above. We do not access your Google Contacts, Drive files, or any other Google
          data not listed here.
        </p>
      </LegalSection>

      <LegalSection number="4" title="How We Use Information">
        <p>We use the information we collect to:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>Provide and operate WorkForge</li>
          <li>Authenticate you and secure your account</li>
          <li>Provide the automation features you configure (tasks, workflows, scheduled commits, and similar)</li>
          <li>Operate the Google integrations you choose to connect</li>
          <li>Maintain and improve the reliability and security of the service</li>
          <li>Communicate with you about your account or the service, where necessary</li>
        </ul>
      </LegalSection>

      <LegalSection number="5" title="Google User Data">
        <p>Specifically regarding data accessed through Google integrations:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>You choose whether to authorize each Google integration, and can disconnect it at any time.</li>
          <li>We only request the Google permissions necessary for the specific features you use.</li>
          <li>We do not sell Google user data.</li>
          <li>We do not use Google user data for advertising.</li>
          <li>
            We do not share Google user data with third parties, except where necessary to provide the
            feature you authorized (for example, sending a request to Google's own APIs on your behalf) or
            where required by law.
          </li>
        </ul>
      </LegalSection>

      <LegalSection number="6" title="Data Storage and Security">
        <p>
          Your data is stored using Supabase, a hosted database and authentication provider. Connected
          third-party access tokens (such as your GitHub or Google tokens) are stored encrypted and are used
          only to act on your behalf within WorkForge for the features you've enabled. We take reasonable
          measures to protect your information, but no method of transmission or storage is completely
          secure, and we cannot guarantee absolute security.
        </p>
      </LegalSection>

      <LegalSection number="7" title="Third-Party Services">
        <p>WorkForge relies on the following third-party infrastructure and services to operate:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li><span className="text-[var(--color-text-primary)]">Supabase</span> — database, authentication, and storage</li>
          <li><span className="text-[var(--color-text-primary)]">Google OAuth &amp; Google APIs</span> — for optional Gmail and Calendar integrations</li>
          <li><span className="text-[var(--color-text-primary)]">GitHub OAuth &amp; API</span> — for optional GitHub integrations (repositories, pull requests, commit scheduling)</li>
          <li><span className="text-[var(--color-text-primary)]">Render</span> — application hosting for our backend</li>
          <li><span className="text-[var(--color-text-primary)]">Resend</span> — transactional email delivery (e.g. verification codes)</li>
          <li><span className="text-[var(--color-text-primary)]">Google Gemini API</span> — used to power certain AI-generated summaries within the app</li>
        </ul>
        <p>Each of these providers processes data only as necessary to provide their respective service to us.</p>
      </LegalSection>

      <LegalSection number="8" title="Data Retention">
        <p>
          We retain your information for as long as your account is active, and only as long as necessary to
          provide the service and meet legitimate business or legal requirements. If you delete your account,
          we remove your account data in accordance with the deletion process available in your account
          settings.
        </p>
      </LegalSection>

      <LegalSection number="9" title="User Rights and Choices">
        <p>You can, at any time:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>Disconnect any connected Google or GitHub integration from your Integrations settings</li>
          <li>Request deletion of your account and associated data from your Settings page</li>
          <li>Stop using the service at any time</li>
          <li>Contact us with any privacy questions using the details below</li>
        </ul>
      </LegalSection>

      <LegalSection number="10" title="Children's Privacy">
        <p>
          WorkForge is not directed to, and is not intended for use by, children. We do not knowingly collect
          personal information from children.
        </p>
      </LegalSection>

      <LegalSection number="11" title="Changes to This Privacy Policy">
        <p>
          We may update this Privacy Policy from time to time. Any changes will be posted on this page with
          an updated "Last updated" date above.
        </p>
      </LegalSection>

      <LegalSection number="12" title="Contact">
        <p>
          If you have any questions about this Privacy Policy, contact us at{' '}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-[var(--color-signal)] hover:brightness-110">
            {CONTACT_EMAIL}
          </a>.
        </p>
      </LegalSection>
    </LegalPageLayout>
  )
}
