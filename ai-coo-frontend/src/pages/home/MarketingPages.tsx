import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Bell, BriefcaseBusiness, CalendarDays, Check, GitBranch, GitCommitHorizontal, GitPullRequest, ListTodo, Mail, MessageCircle, ShieldCheck, Workflow } from 'lucide-react'
import MarketingHeader from '@/components/layout/MarketingHeader'
import MarketingFooter from '@/components/layout/MarketingFooter'

function Page({ eyebrow, title, intro, children }: { eyebrow?: string; title: string; intro: string; children: ReactNode }) {
  return (
    <div className="home-page flex min-h-screen flex-col bg-[var(--color-void)] text-[var(--color-text-primary)]">
      <MarketingHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-5 pb-24 pt-12 sm:px-8 sm:pt-20">
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">{eyebrow}</p>}
        <h1 className={`${eyebrow ? 'mt-4 ' : ''}max-w-4xl font-[family-name:var(--font-display)] text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl`}>{title}</h1>
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
  { icon: ShieldCheck, title: 'Task review and audit logs', detail: 'Review automation-created tasks in one place and inspect workflow results in audit logs.' },
  { icon: BriefcaseBusiness, title: 'Job Hunter', detail: 'Discover job listings, filter the results, and save roles you want to revisit.' },
  { icon: GitPullRequest, title: 'Pull request overview', detail: 'Keep repository pull requests and their review activity visible in your workspace.' },
  { icon: Bell, title: 'Notifications', detail: 'See relevant updates in one place and control which in-app notifications you receive.' },
]

const workflowStages = [
  { number: '01', title: 'An event happens', detail: 'A selected GitHub repository receives a push, issue, or pull request event.', icon: GitBranch },
  { number: '02', title: 'Your rules are checked', detail: 'Conditions decide whether this workflow should continue.', icon: Workflow },
  { number: '03', title: 'Actions run', detail: 'Create a task, send a configured message, or request review.', icon: ListTodo },
  { number: '04', title: 'You see the result', detail: 'Inspect the run and its action results in your workspace.', icon: ShieldCheck },
]

export function FeaturesPage() {
  return (
    <Page title="Project work, connected in one place." intro="Build the workflows you need from connected tools, with clear controls and a record of what happened.">
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {featureCards.map(({ icon: Icon, title, detail }) => (
          <article key={title} className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
            <Icon size={24} className="text-[var(--color-signal)]" />
            <h2 className="mt-5 text-lg font-semibold">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{detail}</p>
          </article>
        ))}
      </div>
      <section className="mt-20">
        <h2 className="max-w-2xl font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">A clear path for work that repeats.</h2>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--color-text-muted)]">Each stage is visible, so you can understand why a workflow ran and what happened next.</p>
        <div className="relative mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {workflowStages.map(({ number, title, detail, icon: Icon }) => (
            <article key={number} className="relative rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
              <div className="flex items-center justify-between"><span className="font-mono text-xs text-[var(--color-signal)]">{number} / 04</span><Icon size={20} className="text-[var(--color-signal)]" /></div>
              <h3 className="mt-8 text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{detail}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="mt-20 grid gap-8 rounded-[1.75rem] border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-signal-dim)] via-[var(--color-surface)] to-[var(--color-surface)] p-7 sm:p-10 lg:grid-cols-[1fr_1.1fr] lg:gap-12">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">Built for oversight</p>
          <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight">Keep the work visible.</h2>
          <p className="mt-4 text-sm leading-7 text-[var(--color-text-muted)]">WorkForge brings the setup and the outcome together. Start with a single rule, review how it behaves, and expand only when it is useful.</p>
          <Link to="/how-it-works" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-[var(--color-signal)]">See how to use it <ArrowRight size={16} /></Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-void)]/65 p-5"><Check size={17} className="text-[var(--color-signal)]" /><h3 className="mt-4 font-semibold">Choose your scope</h3><p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">Connect only the services and repositories a workflow needs.</p></div>
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-void)]/65 p-5"><ShieldCheck size={17} className="text-[var(--color-signal)]" /><h3 className="mt-4 font-semibold">Review proposed tasks</h3><p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">Approve or reject automation-created tasks from the Tasks page.</p></div>
        </div>
      </section>
    </Page>
  )
}

const steps = [
  { number: '01', title: 'Connect the services you choose', detail: 'Authorize GitHub, Gmail, or Google Calendar separately. Configure Discord with an organization webhook.' },
  { number: '02', title: 'Define a trigger and conditions', detail: 'Choose a supported event, then narrow it by repository, branch, or other workflow conditions.' },
  { number: '03', title: 'Choose actions and review tasks', detail: 'Create tasks, send email, notify Discord, or record an audit entry. Review, approve, or reject created tasks from the Tasks page.' },
  { number: '04', title: 'Review each result', detail: 'See recent runs and action results in the workflow and audit views. Scheduled work has its own job controls.' },
]

export function HowItWorksPage() {
  return (
    <Page title="You decide what runs." intro="Start with one connected service and one workflow. WorkForge follows the triggers, conditions, and actions you configure.">
      <div className="mt-12 grid gap-4 md:grid-cols-2">
        {steps.map((step) => (
          <article key={step.number} className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-7">
            <span className="font-mono text-sm text-[var(--color-signal)]">STEP {step.number}</span>
            <h2 className="mt-5 text-xl font-semibold">{step.title}</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--color-text-muted)]">{step.detail}</p>
          </article>
        ))}
      </div>
      <section className="mt-20 grid gap-10 rounded-[1.75rem] border border-[var(--color-border)] bg-[var(--color-surface)] p-7 sm:p-10 lg:grid-cols-[0.85fr_1.15fr]">
        <div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">An example</p><h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold">A high-priority issue comes in.</h2><p className="mt-4 text-sm leading-7 text-[var(--color-text-muted)]">You decide which repository and issue details matter. The workflow checks those conditions before taking the actions you selected.</p></div>
        <ol className="space-y-3">
          {[
            ['GitHub reports the issue', 'A supported issue event starts the workflow.'],
            ['Conditions check the issue', 'The rule can narrow results by the details you configure.'],
            ['WorkForge follows your actions', 'For example, create a task and send a Discord notification.'],
            ['You review the outcome', 'The workflow run and audit history show what succeeded or failed.'],
          ].map(([title, detail], index) => (
            <li key={title} className="flex gap-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-void)]/70 p-4"><span className="font-mono text-xs text-[var(--color-signal)]">0{index + 1}</span><div><h3 className="text-sm font-semibold">{title}</h3><p className="mt-1 text-xs leading-5 text-[var(--color-text-muted)]">{detail}</p></div></li>
          ))}
        </ol>
      </section>
      <section className="mt-16 grid gap-4 sm:grid-cols-3">
        {[
          ['Start small', 'Set up one trigger and one action, then confirm the result before adding more.'],
          ['Keep control', 'Pause or edit a workflow as your process changes.'],
          ['Check the record', 'Use recent runs and audit logs to understand what happened.'],
        ].map(([title, detail]) => <article key={title} className="rounded-2xl border border-[var(--color-border)] p-6"><Check size={18} className="text-[var(--color-signal)]" /><h3 className="mt-4 text-lg font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{detail}</p></article>)}
      </section>
      <Link to="/signup" className="mt-10 inline-flex items-center gap-2 rounded-xl bg-[var(--color-signal)] px-5 py-3 text-sm font-semibold text-[var(--color-void)]">Create your workspace <ArrowRight size={16} /></Link>
    </Page>
  )
}

const connections = [
  { icon: GitBranch, title: 'GitHub', detail: 'Connect your GitHub account to work with selected repositories and their events.', uses: ['Choose repositories', 'React to supported GitHub events'] },
  { icon: Mail, title: 'Gmail', detail: 'Authorize send-only access for workflow messages you configure or approve.', uses: ['Send configured messages', 'No inbox reading'] },
  { icon: CalendarDays, title: 'Google Calendar', detail: 'Authorize Calendar access to view upcoming events and create requested events.', uses: ['See upcoming events', 'Create requested events'] },
  { icon: MessageCircle, title: 'Discord', detail: 'Configure an organization webhook for workflow notifications. This is not an OAuth connection.', uses: ['Send workflow updates', 'Use an organization webhook'] },
]

export function ConnectionsPage() {
  return (
    <Page title="Connect only the tools you need." intro="Each connection serves a specific purpose. Open your workspace to connect or manage services for your organization.">
      <div className="mt-12 grid gap-4 sm:grid-cols-2">
        {connections.map(({ icon: Icon, title, detail, uses }) => (
          <article key={title} className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-7">
            <Icon size={25} className="text-[var(--color-signal)]" />
            <h2 className="mt-5 text-xl font-semibold">{title}</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--color-text-muted)]">{detail}</p>
            <ul className="mt-6 space-y-2 border-t border-[var(--color-border)] pt-5">{uses.map((use) => <li key={use} className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]"><Check size={14} className="shrink-0 text-[var(--color-signal)]" />{use}</li>)}</ul>
          </article>
        ))}
      </div>
      <section className="mt-20">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">Your setup</p>
        <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">One connection at a time.</h2>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--color-text-muted)]">You do not need to connect every service. Add a connection when a workflow or workspace feature needs it, then review the permissions before you authorize it.</p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ['01', 'Choose a service', 'Open Integrations in your workspace and select the tool you want to use.'],
            ['02', 'Review access', 'Read the provider permissions or webhook setup before completing the connection.'],
            ['03', 'Use it in context', 'Select the connected service in a workflow or open its workspace page.'],
          ].map(([number, title, detail]) => <article key={number} className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/55 p-6"><span className="font-mono text-sm text-[var(--color-signal)]">STEP {number}</span><h3 className="mt-5 text-lg font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{detail}</p></article>)}
        </div>
      </section>
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
