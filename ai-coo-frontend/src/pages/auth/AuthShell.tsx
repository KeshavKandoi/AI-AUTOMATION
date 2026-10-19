import type { CSSProperties, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, GitBranch, ListTodo, ShieldCheck } from 'lucide-react'
import BrandLogo from '@/components/BrandLogo'

export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="home-page min-h-screen bg-[var(--color-void)] text-[var(--color-text-primary)] lg:grid lg:grid-cols-[minmax(0,1.05fr)_minmax(480px,0.95fr)]">
      <aside
        className="relative hidden min-h-screen flex-col overflow-hidden border-r border-[var(--color-border)] bg-[#101018] px-10 py-9 lg:flex xl:px-16"
        style={{ '--color-text-primary': '#f5f5f7', '--color-text-muted': '#a2a2af', '--color-text-faint': '#727283' } as CSSProperties}
      >
        <div aria-hidden="true" className="pointer-events-none absolute inset-0" style={{ backgroundImage: 'radial-gradient(rgba(255,255,255,.055) 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
        <div aria-hidden="true" className="pointer-events-none absolute -left-40 bottom-0 h-[32rem] w-[32rem] rounded-full bg-pink-600/15 blur-[110px]" />
        <div aria-hidden="true" className="pointer-events-none absolute -right-52 top-0 h-[30rem] w-[30rem] rounded-full bg-indigo-500/10 blur-[120px]" />
        <BrandLogo size="lg" className="relative z-10 w-fit" />

        <div className="relative z-10 my-auto max-w-xl py-16">
          <span className="inline-flex items-center gap-2 rounded-full border border-[var(--color-signal)]/25 bg-[var(--color-signal-dim)] px-3 py-1.5 text-xs font-medium text-[var(--color-signal)]"><span className="h-1.5 w-1.5 rounded-full bg-[var(--color-signal)]" /> Your workspace, your rules</span>
          <h2 className="mt-7 font-[family-name:var(--font-display)] text-5xl font-semibold leading-[1.08] tracking-tight xl:text-6xl">Put your work<br />on a <span className="text-[var(--color-signal)]">clear path.</span></h2>
          <p className="mt-6 max-w-md text-base leading-8 text-[var(--color-text-muted)]">Connect the tools you choose. Turn project events into actions, with conditions and approvals you control.</p>

          <div className="mt-12 rounded-[1.5rem] border border-white/10 bg-[#191922]/90 p-5 shadow-2xl shadow-black/30 backdrop-blur-sm">
            <div className="mb-5 flex items-center justify-between border-b border-white/10 pb-4"><span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-text-muted)]">An example workflow</span><span className="rounded-full bg-[var(--color-signal-dim)] px-2.5 py-1 text-[10px] font-semibold text-[var(--color-signal)]">Configured by you</span></div>
            <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr] items-center gap-2">
              <div className="min-w-0 rounded-xl border border-white/10 bg-white/[0.04] p-3"><GitBranch size={17} className="text-[var(--color-signal)]" /><p className="mt-3 text-xs font-semibold">GitHub event</p><p className="mt-1 text-[11px] text-[var(--color-text-muted)]">A new issue</p></div>
              <ArrowRight size={15} className="text-[var(--color-text-faint)]" />
              <div className="min-w-0 rounded-xl border border-white/10 bg-white/[0.04] p-3"><ShieldCheck size={17} className="text-[var(--color-signal)]" /><p className="mt-3 text-xs font-semibold">Conditions</p><p className="mt-1 text-[11px] text-[var(--color-text-muted)]">Check your rules</p></div>
              <ArrowRight size={15} className="text-[var(--color-text-faint)]" />
              <div className="min-w-0 rounded-xl border border-[var(--color-signal)]/25 bg-[var(--color-signal-dim)] p-3"><ListTodo size={17} className="text-[var(--color-signal)]" /><p className="mt-3 text-xs font-semibold">Action</p><p className="mt-1 text-[11px] text-[var(--color-text-muted)]">Create a task</p></div>
            </div>
          </div>
          <div className="mt-7 flex items-center gap-2 text-xs text-[var(--color-text-muted)]"><Check size={15} className="text-[var(--color-signal)]" /> Review what happened in your workspace</div>
        </div>
        <p className="relative z-10 text-xs text-[var(--color-text-faint)]">WorkForge · Automation with clear controls</p>
      </aside>

      <main className="flex min-h-screen flex-col px-5 py-6 sm:px-10 lg:px-12 lg:py-9 xl:px-20">
        <div className="flex items-center justify-between gap-4">
          <BrandLogo size="sm" className="lg:hidden" />
          <Link to="/" className="ml-auto inline-flex items-center gap-2 rounded-lg px-2 py-2 text-sm text-[var(--color-text-muted)] transition hover:text-[var(--color-text-primary)]"><ArrowLeft size={16} /> Back to home</Link>
        </div>
        <div className="mx-auto flex w-full max-w-[470px] flex-1 flex-col justify-center py-10 sm:py-14">
          {children}
        </div>
      </main>
    </div>
  )
}
