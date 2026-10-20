import { Link } from 'react-router-dom'
import AnimatedContent from '@/components/ui/AnimatedContent'
import MarketingHeader from '@/components/layout/MarketingHeader'
import MarketingFooter from '@/components/layout/MarketingFooter'
import OrbitImages from '@/components/ui/OrbitImages'
import WorkflowShowcase from './WorkflowShowcase'
import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarDays,
  ChevronDown,
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
    title: 'Workflows that follow your rules',
    description: 'Choose a GitHub event, add conditions, then select the actions WorkForge should run.',
  },
  {
    icon: GitBranch,
    title: 'GitHub project connections',
    description: 'Connect an account and select a repository for issue, pull request, and push workflows.',
  },
  {
    icon: Mail,
    title: 'Email you configure',
    description: 'Send workflow updates with Gmail. WorkForge does not read your inbox or messages.',
  },
  {
    icon: CalendarDays,
    title: 'Google Calendar actions',
    description: 'View upcoming events and create events you request or approve.',
  },
  {
    icon: GitCommitHorizontal,
    title: 'Scheduled commits',
    description: 'Plan repository work on a schedule and review each job from the scheduler.',
  },
  {
    icon: ShieldCheck,
    title: 'Human review and history',
    description: 'Review tasks created by automations and see workflow results in audit logs.',
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

const FAQS = [
  { question: 'What can WorkForge automate?', answer: 'Create workflows from supported GitHub events, add conditions, then choose actions such as creating tasks, sending email, or notifying Discord.' },
  { question: 'Do I need to connect every service?', answer: 'No. Connect only the services needed for your workflows. Gmail and Google Calendar are optional and each requires your authorization.' },
  { question: 'Does WorkForge read my Gmail inbox?', answer: 'No. Gmail access is used to send configured or approved messages. WorkForge does not read inbox messages.' },
  { question: 'Where can I review workflow activity?', answer: 'Review workflows and recent runs in Workflow Automations. Audit Logs shows workflow activity and action results.' },
  { question: 'How can I check the Google permissions?', answer: 'The Google data use page lists requested scopes and explains how WorkForge uses Gmail and Calendar connections.' },
]

export default function Home() {
  const hasSession = useAuthStore((s) => s.isAuthenticated || Boolean(s.user))
  const [openFaq, setOpenFaq] = useState<number | null>(null)

  return (
    <div className="home-page min-h-screen overflow-hidden bg-void text-text-primary">
      <MarketingHeader />

      <main>
        <section className="relative isolate">
          <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
            <div className="absolute -top-56 left-[8%] h-[34rem] w-[34rem] rounded-full bg-pink-500/[0.10] blur-[120px]" />
            <div className="absolute right-[-10rem] top-24 h-[30rem] w-[30rem] rounded-full bg-fuchsia-600/[0.10] blur-[120px]" />
          </div>
          <div className="mx-auto grid max-w-7xl items-start gap-10 px-5 pb-16 pt-16 sm:px-8 sm:pt-20 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14 lg:pb-20 lg:pt-24">
            <div>
              <h1 className="max-w-2xl font-display text-4xl font-semibold leading-[1.06] tracking-tight sm:text-5xl lg:text-6xl xl:text-7xl">
                <span className="block">Turn project activity</span>
                <span className="block">into <span className="text-signal">action.</span></span>
              </h1>
              <p className="mt-6 max-w-xl text-base leading-7 text-text-muted sm:text-lg sm:leading-8">
                Connect GitHub and the tools your team relies on. Build workflows that turn repository events into tasks, emails, scheduled commits, and team notifications—with conditions and clear task review.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                {hasSession ? (
                  <Link to="/dashboard" className="inline-flex items-center gap-2 rounded-xl bg-signal px-5 py-3.5 text-sm font-semibold text-void transition hover:brightness-110">Open workspace <ArrowRight size={16} /></Link>
                ) : (
                  <Link to="/signup" className="inline-flex items-center gap-2 rounded-xl bg-signal px-5 py-3.5 text-sm font-semibold text-void transition hover:brightness-110">Create your workspace <ArrowRight size={16} /></Link>
                )}
                <Link to="/how-it-works" className="inline-flex items-center rounded-xl border border-border px-5 py-3.5 text-sm font-semibold text-text-primary transition hover:border-border-hover hover:bg-surface">See how it works</Link>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-xl">
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
                    <div className="star-border-card flex h-full w-full flex-col items-center justify-center gap-2 rounded-2xl bg-surface px-2 text-signal shadow-xl shadow-black/30">
                      <FeatureIcon size={28} />
                      <span className="text-center text-[11px] font-medium leading-tight text-text-primary">{feature.name}</span>
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
            </div>
          </div>
        </section>

        <section id="features" className="scroll-mt-24 bg-surface/25">
          <div className="mx-auto max-w-7xl px-5 pb-20 pt-10 sm:px-8 sm:pt-12 lg:pb-24">
            <div className="max-w-2xl">
              <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">Less repetitive work. More visibility.</h2>
              <p className="mt-4 text-sm leading-6 text-text-muted sm:text-base">Bring project events and operational follow-up into workflows you can configure and review.</p>
            </div>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature, index) => (
                <AnimatedContent key={feature.title} delay={index * 0.04}>
                  <article className="group h-full rounded-2xl border border-border bg-void/70 p-5 transition duration-200 hover:-translate-y-1 hover:border-signal/40 hover:bg-surface/70 sm:p-6">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-signal-dim text-signal"><feature.icon size={18} /></span>
                    <h3 className="mt-5 text-base font-semibold">{feature.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-text-muted">{feature.description}</p>
                  </article>
                </AnimatedContent>
              ))}
            </div>
          </div>
        </section>

        <section id="product-preview" className="mx-auto max-w-7xl scroll-mt-24 px-5 py-16 sm:px-8 lg:py-20">
          <AnimatedContent>
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">See how one event becomes an action.</h2>
              <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-text-muted sm:text-base">Explore examples of triggers, conditions, task creation, and actions you can configure in WorkForge.</p>
            </div>
            <WorkflowShowcase />
          </AnimatedContent>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-20">
          <AnimatedContent className="relative overflow-hidden rounded-[1.75rem] border border-signal/20 bg-gradient-to-br from-signal-dim via-surface to-surface p-7 sm:p-10 lg:p-12">
            <div aria-hidden="true" className="absolute -right-10 -top-24 h-72 w-72 rounded-full bg-pink-300/[0.09] blur-3xl" />
            <div className="relative flex flex-col gap-7 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-2xl"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-signal">Start with one workflow</p><h2 className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">Put your repeatable work on a clear path.</h2><p className="mt-3 text-sm leading-6 text-text-muted">Connect a service, choose what should trigger, and keep the results visible.</p></div>
              {hasSession ? (
                <Link to="/dashboard" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-signal px-5 py-3.5 text-sm font-semibold text-void transition hover:brightness-110">Open workspace <ArrowRight size={16} /></Link>
              ) : (
                <Link to="/signup" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-signal px-5 py-3.5 text-sm font-semibold text-void transition hover:brightness-110">Create your workspace <ArrowRight size={16} /></Link>
              )}
            </div>
          </AnimatedContent>
        </section>

        <section aria-labelledby="faq-heading" className="mx-auto max-w-7xl px-5 pb-20 pt-8 sm:px-8 lg:pb-24">
          <div className="mx-auto max-w-3xl text-center">
            <h2 id="faq-heading" className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">Get to know WorkForge.</h2>
            <p className="mt-4 text-sm leading-6 text-text-muted sm:text-base">A few quick answers about connecting services and running workflows.</p>
          </div>
          <div className="mx-auto mt-9 grid max-w-4xl gap-3">
            {FAQS.map((faq, index) => {
              const isOpen = openFaq === index
              return (
                <div key={faq.question} className={`overflow-hidden rounded-2xl border transition-colors ${isOpen ? 'border-signal/30 bg-surface' : 'border-border bg-surface/55'}`}>
                  <button type="button" className="flex w-full items-center justify-between gap-5 px-5 py-5 text-left sm:px-6" aria-expanded={isOpen} aria-controls={`faq-answer-${index}`} onClick={() => setOpenFaq(isOpen ? null : index)}>
                    <span className="font-semibold">{faq.question}</span>
                    <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-border bg-void/70 text-signal transition-transform ${isOpen ? 'rotate-180' : ''}`}><ChevronDown size={18} /></span>
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div id={`faq-answer-${index}`} initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ type: 'spring', stiffness: 360, damping: 34 }}>
                        <p id={`faq-answer-${index}`} className="px-5 pb-5 text-sm leading-7 text-text-muted sm:px-6 sm:pb-6">{faq.answer}{index === 4 && <> Visit <Link to="/google-data" className="text-signal underline underline-offset-4">Google data use</Link> for requested scopes and details.</>}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })}
          </div>
        </section>
      </main>

      <MarketingFooter />
    </div>
  )
}
