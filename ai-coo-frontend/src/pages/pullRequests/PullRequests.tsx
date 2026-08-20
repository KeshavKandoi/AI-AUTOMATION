import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, GitPullRequest, Search, ExternalLink } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { pullRequestsService, splitRepoFullName, type PRSummary, type PRView } from '@/services/pullRequests'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Badge from '@/components/ui/Badge'
import PRDetailDrawer from './PRDetailDrawer'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

const VIEW_OPTIONS: { value: PRView; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'mine', label: 'Authored by me' },
  { value: 'in_my_repos', label: 'In my repos' },
  { value: 'needs_review', label: 'Needs my review' },
  { value: 'waiting_review', label: 'Waiting on review' },
  { value: 'changes_requested', label: 'Changes requested' },
  { value: 'approved', label: 'Approved' },
  { value: 'merged', label: 'Merged' },
  { value: 'closed', label: 'Closed' },
]

function stateBadge(pr: PRSummary) {
  if (pr.is_merged) return <Badge tone="signal">merged</Badge>
  if (pr.state === 'closed') return <Badge tone="alert">closed</Badge>
  if (pr.is_draft) return <Badge tone="neutral">draft</Badge>
  return <Badge tone="signal">open</Badge>
}

export default function PullRequests() {
  const orgId = useAuthStore((s) => s.user?.organization_id)

  const [view, setView] = useState<PRView>('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<{ owner: string; repo: string; number: number } | null>(null)

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['pull-requests', orgId, view, search],
    queryFn: () => pullRequestsService.listPullRequests(orgId!, view, undefined, undefined, search || undefined),
    enabled: !!orgId,
  })

  const items = data?.items ?? []

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Pull Requests
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            {data ? `${data.total_count} pull request${data.total_count === 1 ? '' : 's'}` : 'Track your GitHub contributions'}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search pull requests..."
            className="w-64 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] pl-8 pr-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]"
          />
        </div>
        <select
          value={view}
          onChange={(e) => setView(e.target.value as PRView)}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)]"
        >
          {VIEW_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        {isFetching && !isLoading && (
          <span className="text-xs text-[var(--color-text-faint)]">Refreshing…</span>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorBanner message="Couldn't load pull requests. Check your GitHub connection, or try disabling ad blockers/privacy extensions for this site." />
      ) : items.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            icon={GitPullRequest}
            title={search ? 'No pull requests match your search' : 'No pull requests here'}
            description="Pull requests you author, review, or watch will show up here."
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((pr) => (
            <Card key={pr.repo_full_name + '#' + pr.number} className="p-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={() => {
                        const parts = splitRepoFullName(pr.repo_full_name)
                        setSelected({ owner: parts[0], repo: parts[1], number: pr.number })
                      }}
                      className="text-sm font-medium text-[var(--color-text-primary)] hover:underline text-left"
                    >
                      {pr.title}
                    </button>
                    {stateBadge(pr)}
                    {pr.labels.slice(0, 3).map((l) => (
                      <Badge key={l} tone="neutral">{l}</Badge>
                    ))}
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">
                    {pr.repo_full_name} · #{pr.number} · by {pr.author.login}
                  </p>
                  <p className="text-[11px] text-[var(--color-text-faint)] mt-1">
                    updated {formatDistanceToNow(new Date(pr.updated_at), { addSuffix: true })}
                    {pr.comments_count > 0 ? ' · ' + pr.comments_count + ' comments' : ''}
                  </p>
                </div>
                <a href={pr.html_url} target="_blank" rel="noreferrer" className="text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)] transition-colors shrink-0" title="Open on GitHub">
                  <ExternalLink size={14} />
                </a>
              </div>
            </Card>
          ))}
        </div>
      )}

      <PRDetailDrawer
        open={!!selected}
        orgId={orgId ?? ''}
        target={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  )
}
