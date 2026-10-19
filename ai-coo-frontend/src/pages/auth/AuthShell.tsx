import type { ReactNode } from 'react'
import BrandLogo from '@/components/BrandLogo'

export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className="home-page relative flex min-h-screen items-center justify-center overflow-hidden bg-void px-4 py-12 text-text-primary sm:px-8">
      <div aria-hidden="true" className="pointer-events-none absolute -top-48 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-signal opacity-[0.06] blur-[120px]" />
      <div className="relative w-full max-w-[520px]">
        <BrandLogo size="md" className="mb-5" />
        {children}
      </div>
    </main>
  )
}
