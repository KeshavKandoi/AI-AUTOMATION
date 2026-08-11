import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Briefcase, Kanban, HeartPulse, Settings2 } from 'lucide-react'
import { jobHunterService } from '@/services/jobHunter'
import Skeleton from '@/components/ui/Skeleton'
import { cn } from '@/lib/utils'
import JobHunterOnboarding from './JobHunterOnboarding'
import JobDiscovery from './JobDiscovery'
import ApplicationTracker from './ApplicationTracker'
import ProviderHealth from './ProviderHealth'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

type Tab = 'jobs' | 'applications' | 'providers'

export default function JobHunter() {
  const [tab, setTab] = useState<Tab>('jobs')
  const [editingPreferences, setEditingPreferences] = useState(false)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['job-hunter', 'preferences'],
    queryFn: () => jobHunterService.getPreferences(),
  })

  if (isLoading) {
    return (
      <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6 md:p-8 max-w-3xl mx-auto">
        <ErrorBanner message="Couldn't load Job Hunter. Please try again." />
      </div>
    )
  }

  if (!data?.onboarding_completed || editingPreferences) {
    return (
      <JobHunterOnboarding
        existing={editingPreferences ? data?.preferences ?? null : null}
        onSaved={() => {
          setEditingPreferences(false)
          refetch()
        }}
      />
    )
  }

  const tabs: { key: Tab; label: string; icon: typeof Briefcase }[] = [
    { key: 'jobs', label: 'Discover', icon: Briefcase },
    { key: 'applications', label: 'Applications', icon: Kanban },
    { key: 'providers', label: 'Provider health', icon: HeartPulse },
  ]

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Job Hunter
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Discover matching roles and track every application in one place
          </p>
        </div>
        <button
          onClick={() => setEditingPreferences(true)}
          className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text-muted)] px-3 py-2 text-xs hover:border-[var(--color-border-hover)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <Settings2 size={13} />
          Preferences
        </button>
      </div>

      <div className="flex items-center gap-1 border-b border-[var(--color-border)]">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              'flex items-center gap-1.5 px-3.5 py-2.5 text-sm border-b-2 -mb-px transition-colors',
              tab === t.key
                ? 'border-[var(--color-signal)] text-[var(--color-signal)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
            )}
          >
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'jobs' && <JobDiscovery />}
      {tab === 'applications' && <ApplicationTracker />}
      {tab === 'providers' && <ProviderHealth />}
    </div>
  )
}
