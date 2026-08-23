import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

interface LegalPageLayoutProps {
  title: string
  lastUpdated: string
  children: React.ReactNode
}

export default function LegalPageLayout({ title, lastUpdated, children }: LegalPageLayoutProps) {
  return (
    <div className="min-h-screen bg-[var(--color-void)] text-[var(--color-text-primary)]">
      <header className="border-b border-[var(--color-border)]">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            to="/login"
            className="font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--color-text-primary)]"
          >
            WorkForge
          </Link>
          <Link
            to="/login"
            className="flex items-center gap-1.5 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <ArrowLeft size={14} />
            Back
          </Link>
        </div>
      </header>

      <main className="max-w-[900px] mx-auto px-6 py-12 md:py-16">
        <h1 className="font-[family-name:var(--font-display)] text-3xl md:text-4xl font-semibold text-[var(--color-text-primary)]">
          {title}
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text-faint)]">Last updated: {lastUpdated}</p>

        <div className="mt-10 flex flex-col gap-8 text-[var(--color-text-muted)] leading-relaxed text-[15px]">
          {children}
        </div>
      </main>

      <footer className="border-t border-[var(--color-border)] mt-12">
        <div className="max-w-4xl mx-auto px-6 py-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-[var(--color-text-faint)]">
          <span>© {new Date().getFullYear()} WorkForge</span>
          <Link to="/privacy" className="hover:text-[var(--color-text-primary)] transition-colors">Privacy Policy</Link>
          <Link to="/terms" className="hover:text-[var(--color-text-primary)] transition-colors">Terms of Service</Link>
        </div>
      </footer>
    </div>
  )
}
