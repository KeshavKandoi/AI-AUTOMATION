import { Link } from 'react-router-dom'
import {
  ArrowDownRight,
  ArrowRight,
  CalendarDays,
  Check,
  CircleDot,
  GitBranch,
  GitCommitHorizontal,
  LayoutDashboard,
  ListTodo,
  Mail,
  MessageCircle,
  Play,
  ScrollText,
  ShieldCheck,
  Workflow,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

const FEATURES = [
  {
    icon: Workflow,
    number: '01',
    title: 'Workflows that follow your rules',
    description: 'Choose a GitHub event, add conditions, then select the actions WorkForge should run.',
  },
  {
    icon: GitBranch,
    number: '02',
    title: 'GitHub project connections',
    description: 'Connect an account and select a repository for issue, pull request, and push workflows.',
  },
  {
    icon: Mail,
    number: '03',
    title: 'Email you configure',
    description: 'Send workflow updates with Gmail. WorkForge does not read your inbox or messages.',
  },
  {
    icon: CalendarDays,
    number: '04',
    title: 'Google Calendar actions',
    description: 'View upcoming events and create events you request or approve.',
  },
  {
    icon: GitCommitHorizontal,
    number: '05',
    title: 'Scheduled commits',
    description: 'Plan repository work on a schedule and review each job from the scheduler.',
  },
  {
    icon: ShieldCheck,
    number: '06',
    title: 'Human review and history',
    description: 'Keep approval steps in your process and see workflow results in audit logs.',
  },
]

const STEPS = [
  {
    number: '01',
    title: 'Connect the services you choose',
    description: 'Authorize GitHub, Gmail, Calendar, or Discord separately. Review each provider’s permissions before approving.',
  },
  {
    number: '02',
    title: 'Build a workflow',
    description: 'Select an event, set conditions, and choose what should happen when those conditions match.',
  },
  {
    number: '03',
    title: 'Review what happened',
    description: 'Check execution results, audit details, scheduled jobs, and any actions that need your approval.',
  },
]

export default function Home() {
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return (
    <div className="min-h-screen overflow-hidden bg-[var(--color-void)] text-[var(--color-text-primary)]">
      <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[var(--color-void)]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3.5 sm:px-8">
          <Link to="/" className="flex items-center gap-3" aria-label="WorkForge home">
            <img src="/favicon-192.png" alt="" className="h-10 w-10 rounded-xl shadow-lg shadow-blue-950/30" />
            <span className="font-[family-name:var(--font-display)] text-xl font-semibold tracking-tight">WorkForge</span>
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-[var(--color-text-muted)] md:flex" aria-label="Main navigation">
            <a href="#features" className="transition hover:text-[var(--color-text-primary)]">Features</a>
            <a href="#how-it-works" className="transition hover:text-[var(--color-text-primary)]">How it works</a>
            <a href="#google-data" className="transition hover:text-[var(--color-text-primary)]">Google data use</a>
          </nav>
          {isAuthenticated ? (
            <Link to="/dashboard" className="inline-flex items-center gap-2 rounded-xl bg-[var(--color-signal)] px-4 py-2.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110">
              <LayoutDashboard size={16} /> Workspace
            </Link>
          ) : (
            <div className="flex items-center gap-3">
              <Link to="/login" className="hidden text-sm font-medium text-[var(--color-text-muted)] transition hover:text-white sm:inline">Sign in</Link>
              <Link to="/signup" className="rounded-xl bg-[var(--color-signal)] px-4 py-2.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110">Get started</Link>
            </div>
          )}
        </div>
      </header>

      <main>
        <section className="relative isolate">
          <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
            <div className="absolute -top-56 left-[8%] h-[34rem] w-[34rem] rounded-full bg-cyan-400/[0.08] blur-[120px]" />
            <div className="absolute right-[-10rem] top-24 h-[30rem] w-[30rem] rounded-full bg-blue-600/[0.10] blur-[120px]" />
          </div>
          <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 pb-20 pt-16 sm:px-8 sm:pt-24 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:pb-28 lg:pt-28">
            <div>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]/70 px-3.5 py-2 text-xs font-medium text-[var(--color-text-muted)]">
                <span className="h-2 w-2 rounded-full bg-[var(--color-signal)] shadow-[0_0_12px_var(--color-signal)]" />
                Automation, with you in control
              </div>
              <h1 className="max-w-3xl font-[family-name:var(--font-display)] text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl xl:text-7xl">
                Make the work around your projects <span className="text-[var(--color-signal)]">flow.</span>
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-7 text-[var(--color-text-muted)] sm:text-lg sm:leading-8">
                WorkForge connects the tools you choose and runs workflows from events you define. Set the conditions, choose the actions, and keep a clear record of each run.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                {isAuthenticated ? (
                  <Link to="/dashboard" className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--color-signal)] px-5 py-3.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110">
                    Open {user?.organization_name || 'your workspace'} <ArrowRight size={16} />
                  </Link>
                ) : (
                  <>
                    <Link to="/signup" className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--color-signal)] px-5 py-3.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110">
                      Create your workspace <ArrowRight size={16} />
                    </Link>
                    <Link to="/login" className="inline-flex items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]/50 px-5 py-3.5 text-sm font-semibold text-[var(--color-text-primary)] transition hover:bg-[var(--color-surface-hover)]">
                      Sign in
                    </Link>
                  </>
                )}
              </div>
              <p className="mt-4 text-xs leading-5 text-[var(--color-text-faint)]">
                Connect only the services you want. Read how WorkForge uses Google data in the{' '}
                <Link to="/privacy" className="text-[var(--color-signal)] underline underline-offset-4">Privacy Policy</Link>.
              </p>
              <div className="mt-9 flex flex-wrap gap-x-6 gap-y-3 border-t border-[var(--color-border)] pt-5 text-xs text-[var(--color-text-faint)]">
                <span className="inline-flex items-center gap-2"><Check size={14} className="text-[var(--color-signal)]" /> You choose the triggers</span>
                <span className="inline-flex items-center gap-2"><Check size={14} className="text-[var(--color-signal)]" /> Organization-scoped integrations</span>
                <span className="inline-flex items-center gap-2"><Check size={14} className="text-[var(--color-signal)]" /> Run history and audit logs</span>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-xl">
              <div aria-hidden="true" className="absolute -inset-5 rounded-[2rem] bg-gradient-to-br from-cyan-400/10 via-transparent to-blue-500/10 blur-2xl" />
              <div className="relative rounded-[1.75rem] border border-[var(--color-border)] bg-[var(--color-surface)]/90 p-5 shadow-2xl shadow-black/30 backdrop-blur sm:p-7">
                <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-5">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--color-text-faint)]">Workflow preview</p>
                    <h2 className="mt-1.5 text-base font-semibold">A flow you define</h2>
                  </div>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-signal)]/30 bg-[var(--color-signal-dim)] px-2.5 py-1 text-[11px] font-semibold text-[var(--color-signal)]"><Play size={11} fill="currentColor" /> Active</span>
                </div>
                <div className="mt-5 rounded-2xl border border-[var(--color-border)] bg-[var(--color-void)]/70 p-4 sm:p-5">
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]"><GitBranch size={17} /></span>
                    <div className="min-w-0"><p className="text-[11px] uppercase tracking-wider text-[var(--color-text-faint)]">When</p><p className="mt-1 text-sm font-medium">A commit is pushed</p><p className="mt-1 text-xs text-[var(--color-text-faint)]">to a repository you connected</p></div>
                  </div>
                  <div className="ml-[17px] h-7 border-l border-dashed border-[var(--color-border-hover)]" />
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-400/10 text-amber-300"><CircleDot size={17} /></span>
                    <div><p className="text-[11px] uppercase tracking-wider text-[var(--color-text-faint)]">Check</p><p className="mt-1 text-sm font-medium">Your conditions match</p><p className="mt-1 text-xs text-[var(--color-text-faint)]">For example, a branch or commit rule</p></div>
                  </div>
                  <div className="ml-[17px] h-7 border-l border-dashed border-[var(--color-border-hover)]" />
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--color-signal-dim)] text-[var(--color-signal)]"><Workflow size={17} /></span>
                    <div className="min-w-0 flex-1"><p className="text-[11px] uppercase tracking-wider text-[var(--color-text-faint)]">Then</p><p className="mt-1 text-sm font-medium">Run selected actions</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-text-muted)]"><ListTodo size={13} /> Create task</span>
                        <span className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-text-muted)]"><Mail size={13} /> Send email</span>
                        <span className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-text-muted)]"><MessageCircle size={13} /> Notify Discord</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between gap-3 rounded-xl bg-[var(--color-surface-hover)]/60 px-4 py-3 text-xs">
                  <span className="inline-flex items-center gap-2 text-[var(--color-text-muted)]"><ScrollText size={14} className="text-[var(--color-signal)]" /> Execution recorded in audit logs</span>
                  <ArrowDownRight size={15} className="shrink-0 text-[var(--color-text-faint)]" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="scroll-mt-24 border-y border-[var(--color-border)] bg-[var(--color-surface)]/25">
          <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">One workspace, connected tools</p>
              <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">Less repetitive work. More visibility.</h2>
              <p className="mt-4 text-sm leading-6 text-[var(--color-text-muted)] sm:text-base">Bring project events and operational follow-up into workflows you can configure and review.</p>
            </div>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature) => (
                <article key={feature.number} className="group rounded-2xl border border-[var(--color-border)] bg-[var(--color-void)]/70 p-5 transition duration-200 hover:-translate-y-1 hover:border-[var(--color-signal)]/40 hover:bg-[var(--color-surface)]/70 sm:p-6">
                  <div className="flex items-center justify-between">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-signal-dim)] text-[var(--color-signal)]"><feature.icon size={18} /></span>
                    <span className="font-mono text-xs text-[var(--color-text-faint)]">{feature.number}</span>
                  </div>
                  <h3 className="mt-5 text-base font-semibold">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{feature.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="scroll-mt-24">
          <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-2xl">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">A clear setup</p>
                <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">You decide what runs.</h2>
              </div>
              <p className="max-w-md text-sm leading-6 text-[var(--color-text-muted)]">Connected services stay optional. Workflows run from the events and conditions you configure.</p>
            </div>
            <div className="mt-10 grid gap-4 lg:grid-cols-3">
              {STEPS.map((step) => (
                <article key={step.number} className="relative rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/55 p-6 sm:p-7">
                  <p className="font-mono text-sm text-[var(--color-signal)]">STEP {step.number}</p>
                  <h3 className="mt-5 text-lg font-semibold">{step.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{step.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="google-data" className="scroll-mt-24 border-y border-[var(--color-border)] bg-[var(--color-surface)]/25">
          <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
            <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">Google data use</p>
                <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">Clear permissions. Purposeful use.</h2>
                <p className="mt-4 text-sm leading-6 text-[var(--color-text-muted)]">Gmail and Google Calendar are optional connections. WorkForge requests the permissions needed for the features described here; you approve each connection in Google.</p>
                <p className="mt-4 text-sm leading-6 text-[var(--color-text-muted)]">WorkForge does not read Gmail inbox messages. Calendar events are used for event listing and the Calendar actions you request. Calendar event data is not sent to an AI service.</p>
                <Link to="/privacy" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-[var(--color-signal)] underline underline-offset-4 hover:brightness-110">Read the Privacy Policy <ArrowRight size={15} /></Link>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <article className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-void)]/75 p-5 sm:p-6">
                  <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-400/10 text-red-300"><Mail size={18} /></span><h3 className="text-lg font-semibold">Gmail</h3></div>
                  <p className="mt-4 text-sm leading-6 text-[var(--color-text-muted)]">WorkForge sends emails you configure or approve. The connected Google account email identifies the account and can be used as the default recipient when you have not set another recipient.</p>
                  <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">Requested Google scopes</p>
                  <code className="mt-2 block break-all rounded-lg bg-[var(--color-surface)] p-3 text-xs leading-5 text-[var(--color-signal)]">https://www.googleapis.com/auth/gmail.send<br />https://www.googleapis.com/auth/userinfo.email</code>
                  <p className="mt-3 text-xs leading-5 text-[var(--color-text-faint)]">Message addresses, subject, and body are sent to Google for delivery and to the recipients you choose. WorkForge does not access your inbox.</p>
                </article>
                <article className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-void)]/75 p-5 sm:p-6">
                  <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-400/10 text-blue-300"><CalendarDays size={18} /></span><h3 className="text-lg font-semibold">Google Calendar</h3></div>
                  <p className="mt-4 text-sm leading-6 text-[var(--color-text-muted)]">WorkForge lists upcoming events and creates events you request, approve, or configure in Calendar automation. The event listing displays up to 10 upcoming events.</p>
                  <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-faint)]">Requested Google scope</p>
                  <code className="mt-2 block break-all rounded-lg bg-[var(--color-surface)] p-3 text-xs leading-5 text-[var(--color-signal)]">https://www.googleapis.com/auth/calendar</code>
                  <p className="mt-3 text-xs leading-5 text-[var(--color-text-faint)]">Event details are processed for those Calendar features and are not sent to an AI service.</p>
                </article>
              </div>
            </div>
            <div className="mt-5 flex flex-col gap-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/55 p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div className="flex items-start gap-3"><ShieldCheck size={18} className="mt-0.5 shrink-0 text-[var(--color-signal)]" /><p className="text-sm leading-6 text-[var(--color-text-muted)]">OAuth credentials are encrypted in WorkForge’s database. Disconnecting removes stored tokens, but does not revoke Google’s account grant; you can revoke it in your Google Account permissions.</p></div>
              <a href="https://myaccount.google.com/permissions" target="_blank" rel="noreferrer" className="shrink-0 text-sm font-semibold text-[var(--color-signal)] underline underline-offset-4">Manage Google access</a>
            </div>
            <p className="mt-5 text-xs leading-5 text-[var(--color-text-faint)]">WorkForge’s use and transfer of information received from Google APIs follows the <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noreferrer" className="text-[var(--color-signal)] underline underline-offset-4">Google API Services User Data Policy and Limited Use requirements</a>. See our <Link to="/privacy" className="text-[var(--color-signal)] underline underline-offset-4">Privacy Policy</Link> for retention and account deletion details.</p>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-20">
          <div className="relative overflow-hidden rounded-[1.75rem] border border-[var(--color-signal)]/20 bg-gradient-to-br from-[var(--color-signal-dim)] via-[var(--color-surface)] to-[var(--color-surface)] p-7 sm:p-10 lg:p-12">
            <div aria-hidden="true" className="absolute -right-10 -top-24 h-72 w-72 rounded-full bg-cyan-300/[0.09] blur-3xl" />
            <div className="relative flex flex-col gap-7 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-2xl"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">Start with one workflow</p><h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">Put your repeatable work on a clear path.</h2><p className="mt-3 text-sm leading-6 text-[var(--color-text-muted)]">Connect a service, choose what should trigger, and keep the results visible.</p></div>
              {isAuthenticated ? (
                <Link to="/dashboard" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[var(--color-signal)] px-5 py-3.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110">Open workspace <ArrowRight size={16} /></Link>
              ) : (
                <Link to="/signup" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[var(--color-signal)] px-5 py-3.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110">Create your workspace <ArrowRight size={16} /></Link>
              )}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/20">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-12 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr_1fr] md:gap-8 lg:py-16">
          <div className="max-w-sm">
            <Link to="/" className="inline-flex items-center gap-3" aria-label="WorkForge home">
              <img src="/favicon-192.png" alt="" className="h-11 w-11 rounded-xl" />
              <span className="font-[family-name:var(--font-display)] text-xl font-semibold">WorkForge</span>
            </Link>
            <p className="mt-4 text-sm leading-6 text-[var(--color-text-muted)]">Workflow automation for project work, connected services, and the follow-up in between.</p>
            <p className="mt-4 text-xs text-[var(--color-text-faint)]">You choose what to connect and what each workflow is allowed to do.</p>
          </div>
          <div>
            <h2 className="text-sm font-semibold">Product</h2>
            <div className="mt-4 flex flex-col gap-3 text-sm text-[var(--color-text-muted)]">
              <a href="#features" className="transition hover:text-[var(--color-text-primary)]">Features</a>
              <a href="#how-it-works" className="transition hover:text-[var(--color-text-primary)]">How it works</a>
              <Link to="/signup" className="transition hover:text-[var(--color-text-primary)]">Create an account</Link>
              <Link to="/login" className="transition hover:text-[var(--color-text-primary)]">Sign in</Link>
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold">Google connections</h2>
            <div className="mt-4 flex flex-col gap-3 text-sm text-[var(--color-text-muted)]">
              <a href="#google-data" className="transition hover:text-[var(--color-text-primary)]">Google data use</a>
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
    </div>
  )
}
