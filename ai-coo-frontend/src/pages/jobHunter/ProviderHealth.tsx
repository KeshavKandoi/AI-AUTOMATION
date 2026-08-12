import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, HeartPulse, RefreshCw, XCircle } from 'lucide-react'
import { jobHunterService } from '@/services/jobHunter'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function formatDateTime(iso: string | null): string {
  if (!iso) return 'never'
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function platformLabel(platform: string): string {
  return platform
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export default function ProviderHealth() {
  const queryClient = useQueryClient()

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['job-hunter', 'provider-health'],
    queryFn: () => jobHunterService.getProviderHealth(),
  })

  const runSearchMutation = useMutation({
    mutationFn: () => jobHunterService.runSearchNow(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-hunter', 'provider-health'] })
      queryClient.invalidateQueries({ queryKey: ['job-hunter', 'jobs'] })
    },
  })

  const providers = data?.providers ?? []

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {data && (
            <>
              <Badge tone={data.unhealthy_count === 0 ? 'signal' : 'alert'}>
                {data.unhealthy_count === 0
                  ? 'All providers healthy'
                  : `${data.unhealthy_count} provider${data.unhealthy_count === 1 ? '' : 's'} unhealthy`}
              </Badge>
              {data.unhealthy_platforms.length > 0 && (
                <span className="text-xs text-[var(--color-text-muted)]">
                  {data.unhealthy_platforms.map(platformLabel).join(', ')}
                </span>
              )}
            </>
          )}
        </div>
        <Button
          variant="secondary"
          loading={runSearchMutation.isPending}
          disabled={runSearchMutation.isPending}
          onClick={() => runSearchMutation.mutate()}
        >
          <RefreshCw size={14} className={runSearchMutation.isPending ? 'animate-spin' : ''} />
          Run search
        </Button>
      </div>

      {runSearchMutation.isSuccess && !runSearchMutation.isPending && (
        <div className="rounded-lg border border-[var(--color-signal-dim)] bg-[var(--color-signal-dim)] px-3 py-2 text-xs text-[var(--color-signal)]">
          {runSearchMutation.data.status === "already_running"
            ? "A search is already running for your account - check back shortly."
            : "Search started - provider statuses will update here once it finishes."}
        </div>
      )}
      {runSearchMutation.isError && <ErrorBanner message="Couldn't trigger a search run." />}

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : isError ? (
        <Card className="p-6">
          <ErrorBanner message="Couldn't load provider health." />
          <Button variant="ghost" className="mt-3" onClick={() => refetch()}>
            Retry
          </Button>
        </Card>
      ) : providers.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            icon={HeartPulse}
            title="No provider data yet"
            description="Provider health will appear here once a search has run."
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {providers.map((p) => (
            <Card key={p.platform} className="p-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-medium text-[var(--color-text-primary)]">
                      {platformLabel(p.platform)}
                    </h3>
                    <Badge tone={p.is_healthy ? 'signal' : 'alert'}>
                      {p.is_healthy ? (
                        <CheckCircle2 size={11} className="mr-1 inline" />
                      ) : (
                        <XCircle size={11} className="mr-1 inline" />
                      )}
                      {p.is_healthy ? 'Healthy' : 'Unhealthy'}
                    </Badge>
                    <Badge tone="neutral">{p.status}</Badge>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-[var(--color-text-muted)]">
                    <span>Last run: {formatDateTime(p.last_run_at)}</span>
                    <span>Last success: {formatDateTime(p.last_success_at)}</span>
                    <span>Jobs found last run: {p.jobs_found_last_run}</span>
                  </div>
                  {p.last_error && (
                    <p className="text-xs text-[var(--color-alert)] mt-2">{p.last_error}</p>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
