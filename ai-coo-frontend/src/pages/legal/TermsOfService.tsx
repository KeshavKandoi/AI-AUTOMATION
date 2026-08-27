import LegalPageLayout from './LegalPageLayout'
import LegalSection from './LegalSection'

const CONTACT_EMAIL = 'testerappp2001@gmail.com'
const LAST_UPDATED = 'August 23, 2026'

export default function TermsOfService() {
  return (
    <LegalPageLayout title="Terms of Service" lastUpdated={LAST_UPDATED}>
      <LegalSection number="1" title="Acceptance of Terms">
        <p>
          By accessing or using WorkForge, you agree to be bound by these Terms of Service. If you do not
          agree to these terms, do not use the service.
        </p>
      </LegalSection>

      <LegalSection number="2" title="Description of WorkForge">
        <p>
          WorkForge is an automation platform that helps you manage tasks, workflows, and optional
          integrations with services such as GitHub, Gmail, and Google Calendar. Features include task
          tracking, workflow automation, scheduled commits, pull request management, and related
          productivity tools.
        </p>
      </LegalSection>

      <LegalSection number="3" title="User Accounts">
        <p>
          You are responsible for maintaining the confidentiality of your account credentials and for all
          activity that occurs under your account. You agree to provide accurate information when creating
          and maintaining your account.
        </p>
      </LegalSection>

      <LegalSection number="4" title="Google Integrations">
        <p>
          You may optionally connect Google services (Gmail, Google Calendar) to WorkForge. By connecting
          these services, you authorize WorkForge to access the specific permissions you approve during the
          Google consent process, solely to provide the corresponding features within the app.
        </p>
      </LegalSection>

      <LegalSection number="5" title="Acceptable Use">
        <p>You agree not to:</p>
        <ul className="list-disc list-inside flex flex-col gap-1.5">
          <li>Misuse the service or use it for any unlawful purpose</li>
          <li>Attempt to gain unauthorized access to any part of the service or its systems</li>
          <li>Interfere with or disrupt the integrity or performance of the service</li>
          <li>Abuse WorkForge's APIs or third-party integrations in ways not intended by their design</li>
        </ul>
      </LegalSection>

      <LegalSection number="6" title="User Content and Data">
        <p>
          You retain ownership of any content and information you provide to WorkForge. You are responsible
          for the accuracy and legality of the information you submit through the service.
        </p>
      </LegalSection>

      <LegalSection number="7" title="Third-Party Services">
        <p>
          WorkForge relies on third-party services to operate, including Supabase, Google APIs, GitHub APIs,
          Render, Resend, and the Google Gemini API. Your use of any connected third-party service is also
          subject to that provider's own terms.
        </p>
      </LegalSection>

      <LegalSection number="8" title="Availability">
        <p>
          WorkForge is provided on an ongoing basis, but we do not guarantee uninterrupted or error-free
          availability of the service.
        </p>
      </LegalSection>

      <LegalSection number="9" title="Account Suspension or Termination">
        <p>
          We may suspend or terminate your access to WorkForge if you violate these Terms, misuse the
          service, or where required to protect the security or integrity of the platform.
        </p>
      </LegalSection>

      <LegalSection number="10" title="Disclaimer">
        <p>
          WorkForge is provided "as is" and "as available," without warranties of any kind, express or
          implied, to the fullest extent permitted by law.
        </p>
      </LegalSection>

      <LegalSection number="11" title="Limitation of Liability">
        <p>
          To the fullest extent permitted by law, WorkForge and its operators shall not be liable for any
          indirect, incidental, special, consequential, or punitive damages arising from your use of, or
          inability to use, the service.
        </p>
      </LegalSection>

      <LegalSection number="12" title="Changes to the Service and Terms">
        <p>
          We may modify or discontinue parts of the service, and may update these Terms from time to time.
          Continued use of WorkForge after changes take effect constitutes acceptance of the updated Terms.
        </p>
      </LegalSection>

      <LegalSection number="13" title="Governing Law">
        <p>
          These Terms are governed by the laws applicable to WorkForge's place of operation, without regard
          to conflict-of-law principles. This section will be updated to name a specific jurisdiction once
          WorkForge's operating entity and location are finalized.
        </p>
      </LegalSection>

      <LegalSection number="14" title="Contact">
        <p>
          If you have any questions about these Terms, contact us at{' '}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-[var(--color-signal)] hover:brightness-110">
            {CONTACT_EMAIL}
          </a>.
        </p>
      </LegalSection>
    </LegalPageLayout>
  )
}
