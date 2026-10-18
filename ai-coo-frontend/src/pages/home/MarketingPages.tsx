import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CalendarDays, Check, GitBranch, GitCommitHorizontal, Mail, MessageCircle, ShieldCheck, Workflow } from 'lucide-react'
import MarketingHeader from '@/components/layout/MarketingHeader'
import MarketingFooter from '@/components/layout/MarketingFooter'

function Page({ eyebrow, title, intro, children }: { eyebrow: string; title: string; intro: string; children: ReactNode }) {
  return (
    <div className="home-page flex min-h-screen flex-col bg-[var(--color-void)] text-[var(--color-text-primary)]">
      <MarketingHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-5 pb-24 pt-12 sm:px-8 sm:pt-20">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">{eyebrow}</p>
        <h1 className="mt-4 max-w-4xl font-[family-name:var(--font-display)] text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">{title}</h1>
        <p className="mt-5 max-w-2xl text-base leading-8 text-[var(--color-text-muted)] sm:text-lg">{intro}</p>
        {children}
      </main>
      <MarketingFooter />
    </div>
  )
}

const featureCards = [
  { icon: Workflow, title: 'Workflow automations', detail: 'Choose a GitHub event, apply conditions, and decide which actions run.' },
  { icon: GitBranch, title: 'GitHub projects', detail: 'Connect an account and select repositories for push, issue, and pull request workflows.' },
  { icon: Mail, title: 'Gmail sending', detail: 'Send messages you configure or approve. WorkForge does not read your Gmail inbox.' },
  { icon: CalendarDays, title: 'Google Calendar', detail: 'View upcoming events and create events you request or approve.' },
  { icon: GitCommitHorizontal, title: 'Commit Scheduler', detail: 'Plan repository commits and review scheduled jobs.' },
  { icon: ShieldCheck, title: 'Approvals and audit logs', detail: 'Add human review where needed and inspect the result of each run.' },
]

export function FeaturesPage() {
  return (
    <Page eyebrow="Features" title="Project work, connected in one place." intro="Build the workflows you need from connected tools, with clear controls and a record of what happened.">
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {featureCards.map(({ icon: Icon, title, detail }) => (
          <article key={title} className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
            <Icon size={24} className="text-[var(--color-signal)]" />
            <h2 className="mt-5 text-lg font-semibold">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{detail}</p>
          </article>
        ))}
      </div>
      <figure className="mt-12 overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="overflow-x-auto"><img src="/workflow-automations-demo.png" alt="WorkForge Workflow Automations page with example workflows" width={1440} height={650} className="block h-auto min-w-[720px] w-full" /></div>
        <figcaption className="px-5 py-3 text-xs text-[var(--color-text-muted)]">Actual WorkForge interface shown with example data. <span className="sm:hidden">Swipe to see more.</span></figcaption>
      </figure>
    </Page>
  )
}

const steps = [
  { number: '01', title: 'Connect the services you choose', detail: 'Authorize GitHub, Gmail, or Google Calendar separately. Configure Discord with an organization webhook.' },
  { number: '02', title: 'Define a trigger and conditions', detail: 'Choose a supported event, then narrow it by repository, branch, or other workflow conditions.' },
  { number: '03', title: 'Choose actions and approvals', detail: 'Create a task, send an email, notify Discord, or record an audit entry. Add human approval where the workflow calls for it.' },
  { number: '04', title: 'Review each result', detail: 'See recent runs and action results in the workflow and audit views. Scheduled work has its own job controls.' },
]

export function HowItWorksPage() {
  return (
    <Page eyebrow="How it works" title="You decide what runs." intro="Start with one connected service and one workflow. WorkForge follows the triggers, conditions, and actions you configure.">
      <div className="mt-12 grid gap-4 md:grid-cols-2">
        {steps.map((step) => (
          <article key={step.number} className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-7">
            <span className="font-mono text-sm text-[var(--color-signal)]">STEP {step.number}</span>
            <h2 className="mt-5 text-xl font-semibold">{step.title}</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--color-text-muted)]">{step.detail}</p>
          </article>
        ))}
      </div>
      <Link to="/signup" className="mt-10 inline-flex items-center gap-2 rounded-xl bg-[var(--color-signal)] px-5 py-3 text-sm font-semibold text-[var(--color-void)]">Create your workspace <ArrowRight size={16} /></Link>
    </Page>
  )
}

const connections = [
  { icon: GitBranch, title: 'GitHub', detail: 'Connect your GitHub account to work with selected repositories and their events.' },
  { icon: Mail, title: 'Gmail', detail: 'Authorize send-only access for workflow messages you configure or approve.' },
  { icon: CalendarDays, title: 'Google Calendar', detail: 'Authorize Calendar access to view upcoming events and create requested events.' },
  { icon: MessageCircle, title: 'Discord', detail: 'Configure an organization webhook for workflow notifications. This is not an OAuth connection.' },
]

export function ConnectionsPage() {
  return (
    <Page eyebrow="Integrations" title="Connect only the tools you need." intro="Each connection serves a specific purpose. Open your workspace to connect or manage services for your organization.">
      <div className="mt-12 grid gap-4 sm:grid-cols-2">
        {connections.map(({ icon: Icon, title, detail }) => (
          <article key={title} className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-7">
            <Icon size={25} className="text-[var(--color-signal)]" />
            <h2 className="mt-5 text-xl font-semibold">{title}</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--color-text-muted)]">{detail}</p>
          </article>
        ))}
      </div>
      <div className="mt-10 flex flex-wrap gap-4">
        <Link to="/integrations" className="inline-flex items-center gap-2 rounded-xl bg-[var(--color-signal)] px-5 py-3 text-sm font-semibold text-[var(--color-void)]">Manage connections <ArrowRight size={16} /></Link>
        <Link to="/google-data" className="inline-flex items-center gap-2 rounded-xl border border-[var(--color-border)] px-5 py-3 text-sm font-semibold">How Google data is used</Link>
      </div>
    </Page>
  )
}

export function GoogleDataPage() {
  return (
    <Page eyebrow="Google data use" title="Clear permissions. Purposeful use." intro="Gmail and Google Calendar are optional connections. You approve their permissions separately in Google.">
      <div className="mt-12 grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-7">
          <Mail size={25} className="text-[var(--color-signal)]" />
          <h2 className="mt-5 text-xl font-semibold">Gmail</h2>
          <p className="mt-3 text-sm leading-7 text-[var(--color-text-muted)]">WorkForge uses the connected account email and sends messages you configure or approve. It does not read inbox messages.</p>
          <p className="mt-5 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Requested scopes</p>
          <code className="mt-2 block break-all rounded-lg bg-[var(--color-void)] p-3 text-xs leading-6 text-[var(--color-signal)]">https://www.googleapis.com/auth/gmail.send<br />https://www.googleapis.com/auth/userinfo.email</code>
        </article>
        <article className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-7">
          <CalendarDays size={25} className="text-[var(--color-signal)]" />
          <h2 className="mt-5 text-xl font-semibold">Google Calendar</h2>
          <p className="mt-3 text-sm leading-7 text-[var(--color-text-muted)]">WorkForge lists upcoming events and creates events you request, approve, or configure in Calendar automation. Calendar event data is not sent to an AI service.</p>
          <p className="mt-5 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Requested scope</p>
          <code className="mt-2 block break-all rounded-lg bg-[var(--color-void)] p-3 text-xs leading-6 text-[var(--color-signal)]">https://www.googleapis.com/auth/calendar</code>
        </article>
      </div>
      <div className="mt-5 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 p-6 text-sm leading-7 text-[var(--color-text-muted)]">
        <p className="flex items-start gap-3"><Check size={18} className="mt-1 shrink-0 text-[var(--color-signal)]" /> OAuth credentials are encrypted in WorkForge’s database. Disconnecting removes stored tokens; you can separately revoke the grant in your Google Account permissions.</p>
        <p className="mt-4">Read the <Link to="/privacy" className="text-[var(--color-signal)] underline">Privacy Policy</Link> for data sharing, retention, and deletion details. WorkForge follows the <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noreferrer" className="text-[var(--color-signal)] underline">Google API Services User Data Policy</a>, including its Limited Use requirements.</p>
      </div>
    </Page>
  )
}
