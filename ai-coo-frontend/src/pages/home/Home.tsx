import { Link } from 'react-router-dom'
import AnimatedContent from '@/components/ui/AnimatedContent'
import MarketingHeader from '@/components/layout/MarketingHeader'
import MarketingFooter from '@/components/layout/MarketingFooter'
import OrbitImages from '@/components/ui/OrbitImages'
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarDays,
  GitBranch,
  GitCommitHorizontal,
  Mail,
  MessageCircle,
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

const ORBIT_ITEMS = [
  { src: '/workforge-icon.svg', alt: 'GitHub' },
  { src: '/workforge-icon.svg', alt: 'Gmail' },
  { src: '/workforge-icon.svg', alt: 'Google Calendar' },
  { src: '/workforge-icon.svg', alt: 'Commit Scheduler' },
  { src: '/workforge-icon.svg', alt: 'Job Hunter' },
  { src: '/workforge-icon.svg', alt: 'Discord' },
]

export default function Home() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return (
    <div className="home-page min-h-screen overflow-hidden bg-[var(--color-void)] text-[var(--color-text-primary)]">
      <MarketingHeader />

      <main>
        <section className="relative isolate">
          <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
            <div className="absolute -top-56 left-[8%] h-[34rem] w-[34rem] rounded-full bg-pink-500/[0.10] blur-[120px]" />
            <div className="absolute right-[-10rem] top-24 h-[30rem] w-[30rem] rounded-full bg-fuchsia-600/[0.10] blur-[120px]" />
          </div>
          <div className="mx-auto grid max-w-7xl items-start gap-10 px-5 pb-16 pt-16 sm:px-8 sm:pt-20 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14 lg:pb-20 lg:pt-24">
            <AnimatedContent>
              <h1 className="max-w-3xl font-[family-name:var(--font-display)] text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl xl:text-7xl">
                Make the work around your projects <span className="text-[var(--color-signal)]">flow.</span>
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-7 text-[var(--color-text-muted)] sm:text-lg sm:leading-8">
                Connect GitHub, Gmail, Calendar, and Discord. Turn project events into tasks, emails, and notifications with conditions and approvals you control.
              </p>
            </AnimatedContent>

            <AnimatedContent className="relative mx-auto w-full max-w-xl">
              <div aria-hidden="true" className="absolute inset-8 rounded-full bg-pink-500/10 blur-3xl" />
              <OrbitImages
                images={ORBIT_ITEMS}
                renderItem={(_, index) => {
                  const orbitalFeatures = [
                    { name: 'GitHub', icon: GitBranch },
                    { name: 'Gmail', icon: Mail },
                    { name: 'Calendar', icon: CalendarDays },
                    { name: 'Commit Scheduler', icon: GitCommitHorizontal },
                    { name: 'Job Hunter', icon: BriefcaseBusiness },
                    { name: 'Discord', icon: MessageCircle },
                  ]
                  const feature = orbitalFeatures[index]
                  const FeatureIcon = feature.icon
                  return (
                    <div className="star-border-card flex h-full w-full flex-col items-center justify-center gap-2 rounded-2xl bg-[var(--color-surface)] px-2 text-[var(--color-signal)] shadow-xl shadow-black/30">
                      <FeatureIcon size={28} />
                      <span className="text-center text-[11px] font-medium leading-tight text-[var(--color-text-primary)]">{feature.name}</span>
                    </div>
                  )
                }}
                shape="circle"
                baseWidth={1000}
                radius={340}
                itemSize={190}
                duration={30}
                rotation={-7}
                depth={0.08}
                hoverSpeed={0}
                showPath
                pathColor="rgba(255, 0, 110, 0.22)"
                pathWidth={1.5}
                width="100%"
                className="max-w-[38rem]"
                draggable={false}
                clickToFront={false}
                intro
              />
            </AnimatedContent>
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
              {FEATURES.map((feature, index) => (
                <AnimatedContent key={feature.number} delay={index * 0.04}>
                  <article className="group h-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-void)]/70 p-5 transition duration-200 hover:-translate-y-1 hover:border-[var(--color-signal)]/40 hover:bg-[var(--color-surface)]/70 sm:p-6">
                    <div className="flex items-center justify-between">
                      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-signal-dim)] text-[var(--color-signal)]"><feature.icon size={18} /></span>
                      <span className="font-mono text-xs text-[var(--color-text-faint)]">{feature.number}</span>
                    </div>
                    <h3 className="mt-5 text-base font-semibold">{feature.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{feature.description}</p>
                  </article>
                </AnimatedContent>
              ))}
            </div>
          </div>
        </section>

        <section id="product-preview" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-16 sm:px-8 lg:py-20">
          <AnimatedContent>
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">Inside WorkForge</p>
              <h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">See your workflows in one place.</h2>
              <p className="mt-4 text-sm leading-6 text-[var(--color-text-muted)] sm:text-base">Review triggers, conditions, actions, and recent results from the Workflow Automations page.</p>
            </div>
            <figure className="mt-8 overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl shadow-black/30">
              <div className="overflow-x-auto">
                <img
                  src="/workflow-automations-demo.png"
                  alt="WorkForge Workflow Automations page showing three example workflows with their triggers, actions, statuses, and recent results"
                  width={1440}
                  height={650}
                  loading="lazy"
                  decoding="async"
                  className="block h-auto min-w-[720px] w-full"
                />
              </div>
              <figcaption className="border-t border-[var(--color-border)] px-5 py-3 text-xs text-[var(--color-text-muted)]">Actual WorkForge interface shown with example data. <span className="sm:hidden">Swipe to see more.</span></figcaption>
            </figure>
          </AnimatedContent>
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
              {STEPS.map((step, index) => (
                <AnimatedContent key={step.number} delay={index * 0.06}>
                  <article className="relative h-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/55 p-6 sm:p-7">
                    <p className="font-mono text-sm text-[var(--color-signal)]">STEP {step.number}</p>
                    <h3 className="mt-5 text-lg font-semibold">{step.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{step.description}</p>
                  </article>
                </AnimatedContent>
              ))}
            </div>
          </div>
        </section>

        <section id="google-data" className="scroll-mt-24 border-y border-[var(--color-border)] bg-[var(--color-surface)]/25">
          <AnimatedContent className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
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
                  <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-signal-dim)] text-[var(--color-signal)]"><CalendarDays size={18} /></span><h3 className="text-lg font-semibold">Google Calendar</h3></div>
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
          </AnimatedContent>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-20">
          <AnimatedContent className="relative overflow-hidden rounded-[1.75rem] border border-[var(--color-signal)]/20 bg-gradient-to-br from-[var(--color-signal-dim)] via-[var(--color-surface)] to-[var(--color-surface)] p-7 sm:p-10 lg:p-12">
            <div aria-hidden="true" className="absolute -right-10 -top-24 h-72 w-72 rounded-full bg-pink-300/[0.09] blur-3xl" />
            <div className="relative flex flex-col gap-7 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-2xl"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-signal)]">Start with one workflow</p><h2 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight sm:text-4xl">Put your repeatable work on a clear path.</h2><p className="mt-3 text-sm leading-6 text-[var(--color-text-muted)]">Connect a service, choose what should trigger, and keep the results visible.</p></div>
              {isAuthenticated ? (
                <Link to="/dashboard" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[var(--color-signal)] px-5 py-3.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110">Open workspace <ArrowRight size={16} /></Link>
              ) : (
                <Link to="/signup" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[var(--color-signal)] px-5 py-3.5 text-sm font-semibold text-[var(--color-void)] transition hover:brightness-110">Create your workspace <ArrowRight size={16} /></Link>
              )}
            </div>
          </AnimatedContent>
        </section>
      </main>

      <MarketingFooter />
    </div>
  )
}
