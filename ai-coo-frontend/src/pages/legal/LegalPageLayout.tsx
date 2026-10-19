import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import BrandLogo from '@/components/BrandLogo'

interface LegalPageLayoutProps {
  title: string
  lastUpdated: string
  children: React.ReactNode
}

export default function LegalPageLayout({ title, lastUpdated, children }: LegalPageLayoutProps) {
  return (
    <div className="min-h-screen bg-void text-text-primary">
      <header className="border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <BrandLogo size="sm" to="/" />
          <Link
            to="/login"
            className="flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft size={14} />
            Back
          </Link>
        </div>
      </header>

      <main className="max-w-[900px] mx-auto px-6 py-12 md:py-16">
        <h1 className="font-display text-3xl md:text-4xl font-semibold text-text-primary">
          {title}
        </h1>
        <p className="mt-2 text-sm text-text-faint">Last updated: {lastUpdated}</p>

        <div className="mt-10 flex flex-col gap-8 text-text-muted leading-relaxed text-[15px]">
          {children}
        </div>
      </main>

      <footer className="border-t border-border mt-12">
        <div className="max-w-4xl mx-auto px-6 py-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-text-faint">
          <span>© {new Date().getFullYear()} WorkForge</span>
          <Link to="/privacy" className="hover:text-text-primary transition-colors">Privacy Policy</Link>
          <Link to="/security" className="hover:text-text-primary transition-colors">Security</Link>
          <Link to="/terms" className="hover:text-text-primary transition-colors">Terms of Service</Link>
        </div>
      </footer>
    </div>
  )
}
