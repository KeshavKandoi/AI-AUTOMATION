import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AlertCircle, ExternalLink, Star, GitFork, Clock } from 'lucide-react'
import { openSourceService } from '@/services/openSource'
import { useAuthStore } from '@/store/authStore'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/Button'
import JobFormModal from '@/pages/commitScheduler/JobFormModal'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

interface OpportunityDetailDrawerProps {
  orgId: string
  issueTarget: { owner: string; repo: string; number: number } | null
  repoTarget: { owner: string; repo: string } | null
  onCloseIssue: () => void
  onCloseRepo: () => void
}

export default function OpportunityDetailDrawer({
  orgId, issueTarget, repoTarget, onCloseIssue, onCloseRepo,
}: OpportunityDetailDrawerProps) {
  const [workOnRepo, setWorkOnRepo] = useState<string | null>(null)
  const [workOnMessage, setWorkOnMessage] = useState('')

  const open = !!issueTarget || !!repoTarget

  const { data: issue, isLoading: issueLoading, isError: issueError } = useQuery({
    queryKey: ['open-source', 'issue-detail', issueTarget?.owner, issueTarget?.repo, issueTarget?.number],
    queryFn: () => openSourceService.getIssue(orgId, issueTarget!.owner, issueTarget!.repo, issueTarget!.number),
    enabled: !!issueTarget,
  })

  const { data: repo, isLoading: repoLoading, isError: repoError } = useQuery({
    queryKey: ['open-source', 'repo-detail', repoTarget?.owner, repoTarget?.repo],
    queryFn: () => openSourceService.getRepository(orgId, repoTarget!.owner, repoTarget!.repo),
    enabled: !!repoTarget,
  })

  const recordMutation = useMutation({
    mutationFn: (args: { resourceType: 'issue' | 'repository'; repoFullName: string; issueNumber?: number; title?: string }) =>
      openSourceService.recordOpportunitySelected(orgId, args.resourceType, args.repoFullName, args.issueNumber, args.title),
  })

  const handleWorkOnIssue = () => {
    if (!issue) return
    recordMutation.mutate({
      resourceType: 'issue',
      repoFullName: issue.repo_full_name,
      issueNumber: issue.number,
      title: issue.title,
    })
    setWorkOnMessage(`Fix: ${issue.title}`)
    setWorkOnRepo(issue.repo_full_name)
  }

  const handleWorkOnRepo = () => {
    if (!repo) return
    recordMutation.mutate({
      resourceType: 'repository',
      repoFullName: repo.full_name,
      title: repo.full_name,
    })
    setWorkOnMessage(`Contribution to ${repo.full_name}`)
    setWorkOnRepo(repo.full_name)
  }

  const title = issueTarget
    ? `${issueTarget.owner}/${issueTarget.repo} #${issueTarget.number}`
    : repoTarget
    ? `${repoTarget.owner}/${repoTarget.repo}`
    : ''

  const handleClose = () => {
    if (issueTarget) onCloseIssue()
    if (repoTarget) onCloseRepo()
  }

  return (
    <>
      <Modal open={open} onClose={handleClose} title={title} className="max-w-2xl">
        <div className="flex flex-col gap-6 max-h-[75vh] overflow-y-auto pr-1">
          {issueTarget && (
            issueLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-full" />
              </div>
            ) : issueError || !issue ? (
              <ErrorBanner message="Couldn't load this issue." />
            ) : (
              <>
                <div>
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <h3 className="text-base font-medium text-[var(--color-text-primary)]">{issue.title}</h3>
                    <a href={issue.html_url} target="_blank" rel="noreferrer" className="text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)]">
                      <ExternalLink size={14} />
                    </a>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <Badge tone={issue.state === 'open' ? 'signal' : 'neutral'}>{issue.state}</Badge>
                    {issue.labels.map((l) => <Badge key={l} tone="neutral">{l}</Badge>)}
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    {issue.repo_full_name} · by {issue.author.login}
                    {issue.assignee ? ` · assigned to ${issue.assignee.login}` : ' · unassigned'}
                  </p>
                  {issue.body && (
                    <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line mt-3 leading-relaxed max-h-64 overflow-y-auto">
                      {issue.body}
                    </p>
                  )}
                </div>

                <div>
                  <h4 className="text-sm font-medium text-[var(--color-text-primary)] mb-2">Comments</h4>
                  {issue.comments.length === 0 ? (
                    <EmptyState icon={Clock} title="No comments yet" />
                  ) : (
                    <div className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded-lg">
                      {issue.comments.map((c) => (
                        <div key={c.id} className="px-3 py-2">
                          <p className="text-xs text-[var(--color-text-primary)] mb-1">{c.author.login}</p>
                          <p className="text-xs text-[var(--color-text-muted)] whitespace-pre-line line-clamp-6">{c.body}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="border-t border-[var(--color-border)] pt-4">
                  <Button className="w-full" onClick={handleWorkOnIssue} loading={recordMutation.isPending}>
                    Work on this
                  </Button>
                  <p className="text-xs text-[var(--color-text-faint)] mt-2">
                    Opens a scheduled commit job for {issue.repo_full_name}, pre-filled to open a pull request.
                  </p>
                </div>
              </>
            )
          )}

          {repoTarget && (
            repoLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-full" />
              </div>
            ) : repoError || !repo ? (
              <ErrorBanner message="Couldn't load this repository." />
            ) : (
              <>
                <div>
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <h3 className="text-base font-medium text-[var(--color-text-primary)]">{repo.full_name}</h3>
                    <a href={repo.html_url} target="_blank" rel="noreferrer" className="text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)]">
                      <ExternalLink size={14} />
                    </a>
                  </div>
                  {repo.description && (
                    <p className="text-sm text-[var(--color-text-muted)] mb-2">{repo.description}</p>
                  )}
                  <div className="flex items-center gap-3 text-xs text-[var(--color-text-faint)] mb-2">
                    <span className="flex items-center gap-1"><Star size={12} /> {repo.stargazers_count.toLocaleString()} stars</span>
                    <span className="flex items-center gap-1"><GitFork size={12} /> {repo.forks_count.toLocaleString()} forks</span>
                    <span>{repo.open_issues_count} open issues</span>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    {repo.language && <Badge tone="neutral">{repo.language}</Badge>}
                    {repo.topics.slice(0, 6).map((t) => <Badge key={t} tone="neutral">{t}</Badge>)}
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    {repo.license_name ?? 'No license specified'}
                    {repo.homepage && (
                      <>
                        {' · '}
                        <a href={repo.homepage} target="_blank" rel="noreferrer" className="text-[var(--color-signal)] hover:underline">
                          {repo.homepage}
                        </a>
                      </>
                    )}
                  </p>
                </div>

                <div className="border-t border-[var(--color-border)] pt-4">
                  <Button className="w-full" onClick={handleWorkOnRepo} loading={recordMutation.isPending}>
                    Work on this
                  </Button>
                  <p className="text-xs text-[var(--color-text-faint)] mt-2">
                    Opens a scheduled commit job for {repo.full_name}, pre-filled to open a pull request.
                  </p>
                </div>
              </>
            )
          )}
        </div>
      </Modal>

      <JobFormModal
        open={!!workOnRepo}
        orgId={orgId}
        job={null}
        onClose={() => setWorkOnRepo(null)}
        onSuccess={() => {
          setWorkOnRepo(null)
          handleClose()
        }}
        initialValues={
          workOnRepo
            ? { repoFullName: workOnRepo, usePr: true, commitMessage: workOnMessage }
            : undefined
        }
      />
    </>
  )
}
