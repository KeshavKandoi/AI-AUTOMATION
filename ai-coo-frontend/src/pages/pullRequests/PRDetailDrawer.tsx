import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle, CheckCircle2, XCircle, Clock, ExternalLink, Sparkles, RefreshCw,
} from 'lucide-react'
import { pullRequestsService, type MergeMethod } from '@/services/pullRequests'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
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

function apiErrorDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') {
    // GitHub errors often arrive as a JSON string like
    // {"message":"Unprocessable Entity","errors":["..."],...} — pull out the
    // first real error message instead of showing raw JSON to the user.
    try {
      const parsed = JSON.parse(detail)
      if (Array.isArray(parsed?.errors) && typeof parsed.errors[0] === 'string') {
        return parsed.errors[0]
      }
      if (typeof parsed?.message === 'string') {
        return parsed.message
      }
    } catch {
      // not JSON — fall through and use the raw string
    }
    return detail
  }
  return fallback
}

function checkToneIcon(c: { status: string; conclusion: string | null }) {
  if (c.status !== 'completed') return { tone: 'amber' as const, Icon: Clock }
  if (c.conclusion === 'success') return { tone: 'signal' as const, Icon: CheckCircle2 }
  if (c.conclusion === 'failure') return { tone: 'alert' as const, Icon: XCircle }
  return { tone: 'neutral' as const, Icon: Clock }
}

interface PRDetailDrawerProps {
  open: boolean
  orgId: string
  target: { owner: string; repo: string; number: number } | null
  onClose: () => void
}

export default function PRDetailDrawer({ open, orgId, target, onClose }: PRDetailDrawerProps) {
  const queryClient = useQueryClient()
  const [commentBody, setCommentBody] = useState('')
  const [requestChangesBody, setRequestChangesBody] = useState('')
  const [confirmMerge, setConfirmMerge] = useState(false)
  const [confirmClose, setConfirmClose] = useState(false)
  const [mergeMethod, setMergeMethod] = useState<MergeMethod>('merge')

  const detailKey = ['pull-requests', 'detail', target?.owner, target?.repo, target?.number]

  const { data: pr, isLoading, isError } = useQuery({
    queryKey: detailKey,
    queryFn: () => pullRequestsService.getPullRequest(orgId, target!.owner, target!.repo, target!.number),
    enabled: open && !!target,
  })

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    refetch: refetchSummary,
    isFetching: summaryFetching,
  } = useQuery({
    queryKey: [...detailKey, 'summary'],
    queryFn: () => pullRequestsService.getSummary(orgId, target!.owner, target!.repo, target!.number),
    enabled: false,
    retry: false,
  })

  const invalidateDetail = () => queryClient.invalidateQueries({ queryKey: detailKey })

  const approveMutation = useMutation({
    mutationFn: () => pullRequestsService.approvePullRequest(orgId, target!.owner, target!.repo, target!.number),
    onSuccess: invalidateDetail,
  })

  const requestChangesMutation = useMutation({
    mutationFn: () => pullRequestsService.requestChanges(orgId, target!.owner, target!.repo, target!.number, requestChangesBody),
    onSuccess: () => {
      setRequestChangesBody('')
      invalidateDetail()
    },
  })

  const commentMutation = useMutation({
    mutationFn: () => pullRequestsService.commentOnPullRequest(orgId, target!.owner, target!.repo, target!.number, commentBody),
    onSuccess: () => {
      setCommentBody('')
      invalidateDetail()
    },
  })

  const mergeMutation = useMutation({
    mutationFn: () => pullRequestsService.mergePullRequest(orgId, target!.owner, target!.repo, target!.number, mergeMethod),
    onSuccess: () => {
      setConfirmMerge(false)
      invalidateDetail()
    },
  })

  const closeMutation = useMutation({
    mutationFn: () => pullRequestsService.closePullRequest(orgId, target!.owner, target!.repo, target!.number),
    onSuccess: () => {
      setConfirmClose(false)
      invalidateDetail()
    },
  })

  const canAct = pr && pr.state === 'open' && !pr.is_merged

  return (
    <Modal open={open} onClose={onClose} title={pr ? `${pr.repo_full_name} #${pr.number}` : 'Pull request'} className="max-w-2xl">
      <div className="flex flex-col gap-6 max-h-[75vh] overflow-y-auto pr-1">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : isError || !pr ? (
          <ErrorBanner message="Couldn't load this pull request." />
        ) : (
          <>
            {/* Header / read-only overview */}
            <div>
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <h3 className="text-base font-medium text-[var(--color-text-primary)]">{pr.title}</h3>
                <a href={pr.html_url} target="_blank" rel="noreferrer" className="text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)]">
                  <ExternalLink size={14} />
                </a>
              </div>
              <div className="flex items-center gap-2 flex-wrap mb-2">
                {pr.is_merged ? <Badge tone="signal">merged</Badge> : pr.state === 'closed' ? <Badge tone="alert">closed</Badge> : pr.is_draft ? <Badge tone="neutral">draft</Badge> : <Badge tone="signal">open</Badge>}
                <Badge tone={pr.review_decision === 'approved' ? 'signal' : pr.review_decision === 'changes_requested' ? 'alert' : 'neutral'}>
                  {pr.review_decision.replace(/_/g, ' ')}
                </Badge>
                {pr.labels.map((l) => <Badge key={l} tone="neutral">{l}</Badge>)}
              </div>
              <p className="text-xs text-[var(--color-text-muted)]">
                {pr.author.login} · {pr.base_branch} ← {pr.head_branch} · +{pr.additions}/-{pr.deletions} · {pr.changed_files} file{pr.changed_files === 1 ? '' : 's'} · {pr.commits_count} commit{pr.commits_count === 1 ? '' : 's'}
              </p>
              {pr.body && (
                <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line mt-3 leading-relaxed">{pr.body}</p>
              )}
            </div>

            {/* AI Summary */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="text-[var(--color-amber)]" />
                  <h4 className="text-sm font-medium text-[var(--color-text-primary)]">AI summary</h4>
                </div>
                {summary !== undefined && (
                  <button onClick={() => refetchSummary()} disabled={summaryFetching} className="text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)]" title="Refresh">
                    <RefreshCw size={13} className={summaryFetching ? 'animate-spin' : ''} />
                  </button>
                )}
              </div>
              {summaryLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : summaryError ? (
                <ErrorBanner message="Couldn't load AI summary." />
              ) : summary === undefined ? (
                <div className="flex flex-col items-start gap-2">
                  <p className="text-xs text-[var(--color-text-faint)]">Uses your AI quota — load on demand.</p>
                  <Button variant="secondary" onClick={() => refetchSummary()}>Load AI summary</Button>
                </div>
              ) : (
                <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line leading-relaxed">{summary}</p>
              )}
            </div>

            {/* Files */}
            <div>
              <h4 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Changed files</h4>
              {pr.files.length === 0 ? (
                <EmptyState icon={Clock} title="No file changes reported" />
              ) : (
                <div className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded-lg">
                  {pr.files.map((f) => (
                    <div key={f.filename} className="flex items-center justify-between gap-3 px-3 py-2 text-xs">
                      <span className="font-mono text-[var(--color-text-primary)] truncate">{f.filename}</span>
                      <span className="shrink-0 text-[var(--color-text-faint)]">
                        {f.status} · <span className="text-[var(--color-signal)]">+{f.additions}</span> <span className="text-[var(--color-alert)]">-{f.deletions}</span>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Checks */}
            <div>
              <h4 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">CI / checks</h4>
              {pr.checks.length === 0 ? (
                <EmptyState icon={Clock} title="No CI checks reported" />
              ) : (
                <div className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded-lg">
                  {pr.checks.map((c) => {
                    const { tone, Icon } = checkToneIcon(c)
                    return (
                      <div key={c.name} className="flex items-center justify-between gap-3 px-3 py-2 text-xs">
                        <span className="text-[var(--color-text-primary)]">{c.name}</span>
                        <Badge tone={tone}><Icon size={11} className="mr-1 inline" />{c.conclusion ?? c.status}</Badge>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Reviews */}
            <div>
              <h4 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Reviews</h4>
              {pr.reviews.length === 0 ? (
                <EmptyState icon={Clock} title="No reviews yet" />
              ) : (
                <div className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded-lg">
                  {pr.reviews.map((r) => (
                    <div key={r.id} className="px-3 py-2">
                      <div className="flex items-center justify-between gap-3 text-xs">
                        <span className="text-[var(--color-text-primary)]">{r.author.login}</span>
                        <Badge tone={r.state === 'APPROVED' ? 'signal' : r.state === 'CHANGES_REQUESTED' ? 'alert' : 'neutral'}>
                          {r.state.toLowerCase().replace(/_/g, ' ')}
                        </Badge>
                      </div>
                      {r.body && <p className="text-xs text-[var(--color-text-muted)] mt-1">{r.body}</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Comments */}
            <div>
              <h4 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Comments</h4>
              {pr.comments.length === 0 ? (
                <EmptyState icon={Clock} title="No comments yet" />
              ) : (
                <div className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded-lg">
                  {pr.comments.map((c) => (
                    <div key={c.id} className="px-3 py-2">
                      <div className="flex items-center justify-between gap-3 text-xs mb-1">
                        <span className="text-[var(--color-text-primary)]">{c.author.login}</span>
                        {c.path && <span className="text-[var(--color-text-faint)] font-mono truncate">{c.path}</span>}
                      </div>
                      <p className="text-xs text-[var(--color-text-muted)]">{c.body}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Actions — clearly separated from read-only content above */}
            {canAct && (
              <div className="border-t border-[var(--color-border)] pt-4 flex flex-col gap-4">
                <h4 className="text-sm font-medium text-[var(--color-text-primary)]">Actions</h4>

                <div className="flex flex-col gap-2">
                  <textarea
                    value={commentBody}
                    onChange={(e) => setCommentBody(e.target.value)}
                    placeholder="Write a comment..."
                    rows={2}
                    className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)] resize-none"
                  />
                  <Button variant="secondary" disabled={!commentBody.trim()} loading={commentMutation.isPending} onClick={() => commentMutation.mutate()}>
                    Comment
                  </Button>
                  {commentMutation.isError && <ErrorBanner message={apiErrorDetail(commentMutation.error, 'Failed to post comment.')} />}
                </div>

                <div className="flex flex-col gap-2">
                  <textarea
                    value={requestChangesBody}
                    onChange={(e) => setRequestChangesBody(e.target.value)}
                    placeholder="Describe the changes you'd like to see..."
                    rows={2}
                    className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)] resize-none"
                  />
                  <Button variant="secondary" disabled={!requestChangesBody.trim()} loading={requestChangesMutation.isPending} onClick={() => requestChangesMutation.mutate()}>
                    Request changes
                  </Button>
                  {requestChangesMutation.isError && <ErrorBanner message={apiErrorDetail(requestChangesMutation.error, 'Failed to request changes.')} />}
                </div>

                <div className="flex items-center gap-2">
                  <Button variant="secondary" loading={approveMutation.isPending} onClick={() => approveMutation.mutate()}>
                    Approve
                  </Button>
                </div>
                {approveMutation.isError && <ErrorBanner message={apiErrorDetail(approveMutation.error, 'Failed to approve.')} />}

                <div className="border-t border-[var(--color-border)] pt-3 flex items-center gap-2 flex-wrap">
                  <select
                    value={mergeMethod}
                    onChange={(e) => setMergeMethod(e.target.value as MergeMethod)}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-2 text-xs text-[var(--color-text-primary)]"
                  >
                    <option value="merge">Merge commit</option>
                    <option value="squash">Squash and merge</option>
                    <option value="rebase">Rebase and merge</option>
                  </select>
                  {confirmMerge ? (
                    <Button variant="primary" className="!bg-[var(--color-alert)] !text-white" loading={mergeMutation.isPending} onBlur={() => setConfirmMerge(false)} onClick={() => mergeMutation.mutate()}>
                      Confirm merge?
                    </Button>
                  ) : (
                    <Button variant="secondary" onClick={() => setConfirmMerge(true)}>Merge</Button>
                  )}

                  {confirmClose ? (
                    <Button variant="primary" className="!bg-[var(--color-alert)] !text-white" loading={closeMutation.isPending} onBlur={() => setConfirmClose(false)} onClick={() => closeMutation.mutate()}>
                      Confirm close?
                    </Button>
                  ) : (
                    <Button variant="ghost" onClick={() => setConfirmClose(true)}>Close PR</Button>
                  )}
                </div>
                {mergeMutation.isError && <ErrorBanner message={apiErrorDetail(mergeMutation.error, 'Failed to merge.')} />}
                {closeMutation.isError && <ErrorBanner message={apiErrorDetail(closeMutation.error, 'Failed to close.')} />}
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  )
}
