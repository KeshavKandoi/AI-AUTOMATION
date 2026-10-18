import { Link } from 'react-router-dom'
import BrandLogo from '@/components/BrandLogo'

export default function MarketingFooter() {
  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/20">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-12 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr_1fr] md:gap-8 lg:py-16">
        <div className="max-w-sm">
          <BrandLogo size="lg" />
          <p className="mt-4 text-sm leading-6 text-[var(--color-text-muted)]">Workflow automation for project work, connected services, and the follow-up in between.</p>
          <p className="mt-4 text-xs text-[var(--color-text-faint)]">You choose what to connect and what each workflow is allowed to do.</p>
        </div>
        <div>
          <h2 className="text-sm font-semibold">Product</h2>
          <div className="mt-4 flex flex-col gap-3 text-sm text-[var(--color-text-muted)]">
            <Link to="/features" className="transition hover:text-[var(--color-text-primary)]">Features</Link>
            <Link to="/how-it-works" className="transition hover:text-[var(--color-text-primary)]">How it works</Link>
            <Link to="/connections" className="transition hover:text-[var(--color-text-primary)]">Integrations</Link>
            <Link to="/signup" className="transition hover:text-[var(--color-text-primary)]">Create an account</Link>
            <Link to="/login" className="transition hover:text-[var(--color-text-primary)]">Sign in</Link>
          </div>
        </div>
        <div>
          <h2 className="text-sm font-semibold">Google connections</h2>
          <div className="mt-4 flex flex-col gap-3 text-sm text-[var(--color-text-muted)]">
            <Link to="/google-data" className="transition hover:text-[var(--color-text-primary)]">Google data use</Link>
            <Link to="/privacy" className="transition hover:text-[var(--color-text-primary)]">Privacy Policy</Link>
            <Link to="/security" className="transition hover:text-[var(--color-text-primary)]">Security</Link>
            <Link to="/terms" className="transition hover:text-[var(--color-text-primary)]">Terms of Service</Link>
          </div>
        </div>
        <div>
          <h2 className="text-sm font-semibold">Support</h2>
          <div className="mt-4 flex flex-col gap-3 text-sm text-[var(--color-text-muted)]">
            <a href="mailto:testerappp2001@gmail.com" className="transition hover:text-[var(--color-text-primary)]">Contact WorkForge</a>
            <a href="https://myaccount.google.com/permissions" target="_blank" rel="noreferrer" className="transition hover:text-[var(--color-text-primary)]">Google Account permissions</a>
          </div>
        </div>
      </div>
      <div className="border-t border-[var(--color-border)]">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-5 py-5 text-xs text-[var(--color-text-faint)] sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>© {new Date().getFullYear()} WorkForge</span>
          <span>Google services are optional and require your authorization.</span>
        </div>
      </div>
    </footer>
  )
}
