import { useQuery } from '@tanstack/react-query'
import { Mail, Sparkles, RefreshCw, AlertCircle } from 'lucide-react'
import { gmailService } from '@/services/gmail'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/Button'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

export default function Gmail() {
  const orgId = useAuthStore((s) => s.user?.organization_id)

  const {
    data: unreadResult,
    isLoading: unreadLoading,
    isError: unreadError,
    refetch: refetchUnread,
    isFetching: unreadFetching,
  } = useQuery({
    queryKey: ['gmail', 'unread', orgId],
    queryFn: () => gmailService.getUnread(orgId!),
    enabled: !!orgId,
    retry: false,
  })

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    refetch: refetchSummary,
    isFetching: summaryFetching,
  } = useQuery({
    queryKey: ['gmail', 'summary', orgId],
    queryFn: () => gmailService.getSummary(orgId!),
    enabled: false,
    retry: false,
  })

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Gmail
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Unread mail and AI-generated summaries
          </p>
        </div>
      </div>

      {/* AI Summary */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-[var(--color-amber)]" />
            <h2 className="text-sm font-medium text-[var(--color-text-primary)]">AI summary</h2>
          </div>
          {summary !== undefined && (
            <button
              onClick={() => refetchSummary()}
              disabled={summaryFetching}
              className="text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)] transition-colors"
              title="Refresh"
            >
              <RefreshCw size={14} className={summaryFetching ? 'animate-spin' : ''} />
            </button>
          )}
        </div>
        {summaryLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : summaryError ? (
          <ErrorBanner message="Couldn't load AI summary. Try refreshing." />
        ) : summary === undefined ? (
          <div className="flex flex-col items-start gap-2">
            <p className="text-xs text-[var(--color-text-faint)]">
              Uses your AI quota — load on demand.
            </p>
            <Button variant="secondary" onClick={() => refetchSummary()}>
              Load AI summary
            </Button>
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line leading-relaxed">
            {summary}
          </p>
        )}
      </Card>

      {/* Unread emails */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)]">
            Unread mail {unreadResult && <span className="text-[var(--color-text-faint)]">({unreadResult.unread_count})</span>}
          </h2>
          <button
            onClick={() => refetchUnread()}
            disabled={unreadFetching}
            className="text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)] transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} className={unreadFetching ? 'animate-spin' : ''} />
          </button>
        </div>

        {unreadLoading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : unreadError ? (
          <ErrorBanner message="Couldn't load unread mail. Try refreshing." />
        ) : !unreadResult || unreadResult.emails.length === 0 ? (
          <EmptyState icon={Mail} title="No unread emails" description="Inbox is clear." />
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {unreadResult.emails.map((email, idx) => (
              <div key={idx} className="py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm text-[var(--color-text-primary)] truncate">
                    {email.from ?? 'Unknown sender'}
                  </p>
                </div>
                <p className="text-sm text-[var(--color-text-muted)] truncate mt-0.5">
                  {email.subject || '(no subject)'}
                </p>
                {email.snippet && (
                  <p className="text-xs text-[var(--color-text-faint)] truncate mt-1">
                    {email.snippet}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
