import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Bell,
  CheckCircle2,
  GitBranch,
  GitPullRequest,
  ListTodo,
  Mail,
  ShieldCheck,
  Split,
  type LucideIcon,
} from 'lucide-react'

type Step = { title: string; detail: string; icon: LucideIcon }
type Example = {
  name: string
  summary: string
  trigger: Step
  condition: Step
  review: Step
  actions: [Step, Step]
}

const EXAMPLES: Example[] = [
  {
    name: 'Issues',
    summary: 'Turn a new issue into a task and a team update.',
    trigger: { title: 'Issue opened', detail: 'GitHub event', icon: GitBranch },
    condition: { title: 'Check labels', detail: 'Your conditions', icon: Split },
    review: { title: 'Match found', detail: 'Continue if true', icon: CheckCircle2 },
    actions: [
      { title: 'Create task', detail: 'Assign follow-up', icon: ListTodo },
      { title: 'Notify team', detail: 'Discord webhook', icon: Bell },
    ],
  },
  {
    name: 'Pull requests',
    summary: 'Route a pull request through your review process.',
    trigger: { title: 'PR opened', detail: 'GitHub event', icon: GitPullRequest },
    condition: { title: 'Check branch', detail: 'Your conditions', icon: Split },
    review: { title: 'Request review', detail: 'Human approval', icon: ShieldCheck },
    actions: [
      { title: 'Create task', detail: 'Track the review', icon: ListTodo },
      { title: 'Send update', detail: 'Configured email', icon: Mail },
    ],
  },
  {
    name: 'Push events',
    summary: 'Keep the right people informed when code changes.',
    trigger: { title: 'Code pushed', detail: 'GitHub event', icon: GitBranch },
    condition: { title: 'Check branch', detail: 'Your conditions', icon: Split },
    review: { title: 'Match found', detail: 'Continue if true', icon: CheckCircle2 },
    actions: [
      { title: 'Notify team', detail: 'Discord webhook', icon: Bell },
      { title: 'Send update', detail: 'Configured email', icon: Mail },
    ],
  },
]

function Node({ step, className, label }: { step: Step; className: string; label: string }) {
  const Icon = step.icon
  return (
    <div className={`absolute z-10 w-[168px] rounded-2xl border border-white/15 bg-[#1b1b25]/95 p-4 shadow-xl shadow-black/25 ${className}`}>
      <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--color-signal-dim)] text-[var(--color-signal)]">
        <Icon size={18} aria-hidden="true" />
      </span>
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--color-text-faint)]">{label}</p>
      <p className="mt-1 text-sm font-semibold leading-5 text-[var(--color-text-primary)]">{step.title}</p>
      <p className="mt-1 text-xs text-[var(--color-text-muted)]">{step.detail}</p>
    </div>
  )
}

export default function WorkflowShowcase() {
  const [selected, setSelected] = useState(0)
  const example = EXAMPLES[selected]

  return (
    <div className="mt-9 overflow-hidden rounded-[1.75rem] border border-[var(--color-border)] bg-[#111019] shadow-2xl shadow-black/25 lg:grid lg:grid-cols-[245px_minmax(0,1fr)]">
      <div className="border-b border-[var(--color-border)] p-4 sm:p-5 lg:border-b-0 lg:border-r">
        <p className="px-3 pb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-faint)]">Choose a starting point</p>
        <div role="tablist" aria-label="Workflow examples" className="flex gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">
          {EXAMPLES.map((item, index) => (
            <button
              key={item.name}
              type="button"
              role="tab"
              aria-selected={selected === index}
              aria-controls="workflow-example"
              onClick={() => setSelected(index)}
              className={`min-w-max rounded-xl border px-4 py-3 text-left text-sm transition-colors lg:min-w-0 ${selected === index ? 'border-[var(--color-signal)]/45 bg-[var(--color-signal-dim)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-muted)] hover:border-[var(--color-border-hover)] hover:bg-white/[0.04] hover:text-[var(--color-text-primary)]'}`}
            >
              <span className="font-semibold">{item.name}</span>
              <span className="mt-1 hidden text-xs leading-5 text-[var(--color-text-muted)] lg:block">{item.summary}</span>
            </button>
          ))}
        </div>
        <p className="mt-5 hidden px-3 text-xs leading-5 text-[var(--color-text-faint)] lg:block">Examples show possible setups. Each workflow runs only after you configure it.</p>
      </div>

      <div id="workflow-example" role="tabpanel" className="min-w-0">
        <div className="flex items-center justify-between gap-4 border-b border-[var(--color-border)] px-5 py-4 sm:px-7">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-signal)]">Example workflow</p>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">{example.summary}</p>
          </div>
          <span className="hidden shrink-0 items-center gap-1.5 rounded-full border border-[var(--color-border)] px-3 py-1.5 text-[11px] text-[var(--color-text-muted)] sm:inline-flex"><span className="h-1.5 w-1.5 rounded-full bg-[var(--color-signal)]" /> Configure your own</span>
        </div>
        <div className="overflow-x-auto">
          <div className="relative h-[390px] min-w-[860px] overflow-hidden" style={{ backgroundImage: 'radial-gradient(rgba(255,255,255,.11) 1px, transparent 1px)', backgroundSize: '22px 22px' }}>
            <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-pink-500/[0.04] to-transparent" />
            <svg aria-hidden="true" className="absolute inset-0 h-full w-full" viewBox="0 0 860 390" preserveAspectRatio="none" fill="none">
              <path d="M188 198 H236 M404 198 H450 M618 198 H650 Q670 198 670 174 V113 H680 M618 198 H650 Q670 198 670 222 V286 H680" stroke="rgba(255,255,255,.28)" strokeWidth="2" />
              <path d="M188 198 H236 M404 198 H450 M618 198 H650 Q670 198 670 174 V113 H680 M618 198 H650 Q670 198 670 222 V286 H680" stroke="var(--color-signal)" strokeWidth="2" strokeDasharray="8 18" className="workflow-flow-line" />
              {[188, 404, 618].map((x) => <circle key={x} cx={x} cy="198" r="5" fill="var(--color-signal)" />)}
            </svg>
            <AnimatePresence mode="wait" initial={false}>
              <motion.div key={selected} className="absolute inset-0" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
                <Node step={example.trigger} label="Trigger" className="left-[20px] top-[135px]" />
                <Node step={example.condition} label="Condition" className="left-[236px] top-[135px]" />
                <Node step={example.review} label="Decision" className="left-[450px] top-[135px]" />
                <Node step={example.actions[0]} label="Action 01" className="left-[680px] top-[50px]" />
                <Node step={example.actions[1]} label="Action 02" className="left-[680px] top-[223px]" />
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
        <div className="border-t border-[var(--color-border)] px-5 py-3 text-xs text-[var(--color-text-faint)] sm:px-7">Illustrative example · Connect only the services each workflow needs. <span className="lg:hidden">Swipe to see the whole flow.</span></div>
      </div>
    </div>
  )
}
