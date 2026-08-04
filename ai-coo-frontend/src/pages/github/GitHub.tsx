import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  GitBranch, Sparkles, ListChecks, Search, Plus, RefreshCw,
  ExternalLink, AlertCircle, CheckCircle2,
} from 'lucide-react'
import { githubService, type GitHubRepo } from '@/services/github'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

export default function GitHub() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [issueModalOpen, setIssueModalOpen] = useState(false)
  const [issueRepo, setIssueRepo] = useState('')
  const [issueTitle, setIssueTitle] = useState('')
  const [issueBody, setIssueBody] = useState('')
  const [connectRepoInput, setConnectRepoInput] = useState('')

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['github'] })
  }

  const {
    data: connectedRepo,
    isLoading: repoLoading,
  } = useQuery({
    queryKey: ['github', 'connected-repo', orgId],
    queryFn: () => githubService.getConnectedRepo(orgId!),
    enabled: !!orgId,
  })

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    refetch: refetchSummary,
    isFetching: summaryFetching,
  } = useQuery({
    queryKey: ['github', 'summary', orgId],
    queryFn: () => githubService.getSummary(orgId!),
    enabled: !!orgId,
    retry: false,
  })

  const {
    data: priorities,
    isLoading: prioritiesLoading,
    isError: prioritiesError,
    refetch: refetchPriorities,
    isFetching: prioritiesFetching,
  } = useQuery({
    queryKey: ['github', 'priorities', orgId],
    queryFn: () => githubService.getPriorities(orgId!),
    enabled: !!orgId,
    retry: false,
  })

  const {
    data: repos,
    isLoading: reposLoading,
    isError: reposError,
  } = useQuery({
    queryKey: ['github', 'repos', orgId],
    queryFn: () => githubService.listRepos(orgId!),
    enabled: !!orgId,
    retry: false,
  })

  const connectRepoMutation = useMutation({
    mutationFn: (repoFullName: string) => githubService.connectRepo(orgId!, repoFullName),
    onSuccess: () => {
      setConnectRepoInput('')
      invalidateAll()
    },
  })

  const createIssueMutation = useMutation({
    mutationFn: () => githubService.createIssue(orgId!, issueRepo, issueTitle, issueBody),
    onSuccess: () => {
      setIssueModalOpen(false)
      setIssueTitle('')
      setIssueBody('')
      invalidateAll()
    },
  })

  const createTasksMutation = useMutation({
    mutationFn: () => githubService.createTasksFromPriorities(orgId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const filteredRepos = useMemo(() => {
    if (!repos) return []
    const q = search.trim().toLowerCase()
    if (!q) return repos
    return repos.filter(
      (r) => r.name.toLowerCase().includes(q) || (r.language ?? '').toLowerCase().includes(q)
    )
  }, [repos, search])

  const openIssueModal = (repoFullName?: string) => {
    setIssueRepo(repoFullName ?? connectedRepo ?? '')
    setIssueModalOpen(true)
  }

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            GitHub
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Repository intelligence and issue management
          </p>
        </div>
        <Button onClick={() => openIssueModal()} disabled={!connectedRepo && filteredRepos.length === 0}>
          <Plus size={15} />
          New issue
        </Button>
      </div>

      {/* Connected repo */}
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <GitBranch size={16} className="text-[var(--color-signal)]" />
          <h2 className="text-sm font-medium text-[var(--color-text-primary)]">Connected repository</h2>
        </div>
        {repoLoading ? (
          <Skeleton className="h-9 w-64" />
        ) : connectedRepo ? (
          <div className="flex items-center gap-2 text-sm text-[var(--color-text-primary)]">
            <CheckCircle2 size={14} className="text-[var(--color-signal)]" />
            
              <a href={`https://github.com/${connectedRepo}`}
              target="_blank"
              rel="noreferrer"
              className="hover:underline flex items-center gap-1"
            >
              {connectedRepo}
              <ExternalLink size={12} />
            </a>
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-faint)] mb-3">No repository connected yet.</p>
        )}
        <div className="flex gap-2 mt-3">
          <Input
            placeholder="owner/repo"
            value={connectRepoInput}
            onChange={(e) => setConnectRepoInput(e.target.value)}
            className="max-w-xs"
          />
          <Button
            variant="secondary"
            disabled={!connectRepoInput.trim()}
            loading={connectRepoMutation.isPending}
            onClick={() => connectRepoMutation.mutate(connectRepoInput.trim())}
          >
            {connectedRepo ? 'Reconnect' : 'Connect'}
          </Button>
        </div>
        {connectRepoMutation.isError && (
          <div className="mt-2">
            <ErrorBanner message="Failed to connect repository. It may already be connected, or the repo name is invalid." />
          </div>
        )}
      </Card>

      {/* AI Summary + Priorities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-[var(--color-amber)]" />
              <h2 className="text-sm font-medium text-[var(--color-text-primary)]">AI summary</h2>
            </div>
            <button
              onClick={() => refetchSummary()}
              disabled={summaryFetching}
              className="text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)] transition-colors"
              title="Refresh"
            >
              <RefreshCw size={14} className={summaryFetching ? 'animate-spin' : ''} />
            </button>
          </div>
          {summaryLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : summaryError ? (
            <ErrorBanner message="Couldn't load AI summary. Try refreshing." />
          ) : (
            <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line leading-relaxed">
              {summary}
            </p>
          )}
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ListChecks size={16} className="text-[var(--color-signal)]" />
              <h2 className="text-sm font-medium text-[var(--color-text-primary)]">Prioritized issues</h2>
            </div>
            <button
              onClick={() => refetchPriorities()}
              disabled={prioritiesFetching}
              className="text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)] transition-colors"
              title="Refresh"
            >
              <RefreshCw size={14} className={prioritiesFetching ? 'animate-spin' : ''} />
            </button>
          </div>
          {prioritiesLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : prioritiesError ? (
            <ErrorBanner message="Couldn't load priorities. Try refreshing." />
          ) : (
            <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line leading-relaxed mb-4">
              {priorities}
            </p>
          )}
          <Button
            variant="secondary"
            className="w-full"
            loading={createTasksMutation.isPending}
            onClick={() => createTasksMutation.mutate()}
          >
            Create tasks from priorities
          </Button>
          {createTasksMutation.isSuccess && (
            <p className="mt-2 text-xs text-[var(--color-signal)]">
              {createTasksMutation.data.tasks_created > 0
                ? `${createTasksMutation.data.tasks_created} task(s) created.`
                : createTasksMutation.data.message ?? 'No new tasks created.'}
            </p>
          )}
          {createTasksMutation.isError && (
            <div className="mt-2">
              <ErrorBanner message="Failed to create tasks from priorities." />
            </div>
          )}
        </Card>
      </div>

      {/* Repos list */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
          <h2 className="text-sm font-medium text-[var(--color-text-primary)]">
            Repositories {repos && <span className="text-[var(--color-text-faint)]">({repos.length})</span>}
          </h2>
          <div className="relative w-full max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search repos..."
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] pl-9 pr-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]"
            />
          </div>
        </div>

        {reposLoading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : reposError ? (
          <ErrorBanner message="Couldn't load repositories." />
        ) : filteredRepos.length === 0 ? (
          <EmptyState
            icon={GitBranch}
            title={search ? 'No repos match your search' : 'No repositories found'}
          />
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {filteredRepos.map((repo: GitHubRepo) => (
              <div key={repo.id} className="flex items-center justify-between gap-4 py-3">
                <div className="min-w-0 flex-1">
                  
                    <a href={repo.html_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-[var(--color-text-primary)] hover:underline flex items-center gap-1 w-fit"
                  >
                    {repo.name}
                    <ExternalLink size={11} />
                  </a>
                  {repo.description && (
                    <p className="text-xs text-[var(--color-text-faint)] truncate mt-0.5 max-w-md">
                      {repo.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {repo.language && <Badge tone="neutral">{repo.language}</Badge>}
                  {repo.open_issues_count > 0 && (
                    <Badge tone="amber">{repo.open_issues_count} open</Badge>
                  )}
                  <Button variant="ghost" onClick={() => openIssueModal(repo.full_name)}>
                    <Plus size={13} />
                    Issue
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Create issue modal */}
      <Modal open={issueModalOpen} onClose={() => setIssueModalOpen(false)} title="New GitHub issue">
        <div className="flex flex-col gap-4">
          <Input
            label="Repository"
            placeholder="owner/repo"
            value={issueRepo}
            onChange={(e) => setIssueRepo(e.target.value)}
          />
          <Input
            label="Title"
            placeholder="Issue title"
            value={issueTitle}
            onChange={(e) => setIssueTitle(e.target.value)}
          />
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--color-text-muted)]">Description</label>
            <textarea
              value={issueBody}
              onChange={(e) => setIssueBody(e.target.value)}
              rows={4}
              placeholder="Optional description"
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)] resize-none"
            />
          </div>
          {createIssueMutation.isError && (
            <ErrorBanner message="Failed to create issue. Check the repository name and try again." />
          )}
          <Button
            className="w-full"
            disabled={!issueRepo.trim() || !issueTitle.trim()}
            loading={createIssueMutation.isPending}
            onClick={() => createIssueMutation.mutate()}
          >
            Create issue
          </Button>
        </div>
      </Modal>
    </div>
  )
}
