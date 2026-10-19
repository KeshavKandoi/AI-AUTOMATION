import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Briefcase, Bookmark } from 'lucide-react'
import { jobHunterService } from '@/services/jobHunter'
import Skeleton from '@/components/ui/Skeleton'
import { cn } from '@/lib/utils'
import JobHunterOnboarding from './JobHunterOnboarding'
import JobDiscovery from './JobDiscovery'
import ApplicationTracker from './ApplicationTracker'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-alert-dim bg-alert-dim px-3 py-2 text-xs text-alert">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

type Tab = 'jobs' | 'applications'

export default function JobHunter() {
  const [tab, setTab] = useState<Tab>('jobs')

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

  if (!data?.onboarding_completed) {
    return (
      <JobHunterOnboarding
        existing={null}
        onSaved={() => refetch()}
      />
    )
  }

  const tabs: { key: Tab; label: string; icon: typeof Briefcase }[] = [
    { key: 'jobs', label: 'Discover', icon: Briefcase },
    { key: 'applications', label: 'Saved jobs', icon: Bookmark },
  ]

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">
            Job Hunter
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Discover roles and keep the jobs you want to revisit
          </p>
        </div>
      </div>

      <div className="flex items-center gap-1 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              'flex items-center gap-1.5 px-3.5 py-2.5 text-sm border-b-2 -mb-px transition-colors',
              tab === t.key
                ? 'border-signal text-signal'
                : 'border-transparent text-text-muted hover:text-text-primary'
            )}
          >
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'jobs' && <JobDiscovery />}
      {tab === 'applications' && <ApplicationTracker />}
    </div>
  )
}
