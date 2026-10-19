import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, useReducedMotion } from 'framer-motion'
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
    <div className="flex items-start gap-2 rounded-lg border border-alert-dim bg-alert-dim px-3 py-2 text-xs text-alert">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function apiErrorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' && detail.trim() ? detail : fallback
}

function FormattedAiText({ text }: { text: string }) {
  const lines = text.split(/\r?\n/)

  return (
    <div className="space-y-2 text-sm leading-relaxed text-text-muted">
      {lines.map((line, index) => {
        const trimmed = line.trim()
        if (!trimmed) return null
        const heading = trimmed.match(/^#{1,6}\s+(.+)$/)
        const listItem = trimmed.match(/^(?:[-*•]|\d+[.)])\s+(.+)$/)
        const content = (heading?.[1] ?? listItem?.[1] ?? trimmed).split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, partIndex) => {
          const bold = part.match(/^\*\*(.+)\*\*$/)
          if (bold) return <strong key={partIndex} className="font-semibold text-text-primary">{bold[1]}</strong>
          const italic = part.match(/^\*(.+)\*$/)
          if (italic) return <em key={partIndex}>{italic[1]}</em>
          return part
        })

        if (heading) return <h3 key={index} className="pt-2 font-semibold text-text-primary">{content}</h3>
        if (listItem) return <p key={index} className="pl-4 before:mr-2 before:content-['•']">{content}</p>
        return <p key={index}>{content}</p>
      })}
    </div>
  )
}

export default function GitHub() {
  const reduceMotion = useReducedMotion()
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const githubConnectResult = searchParams.get('github')

  const [search, setSearch] = useState('')
  const [issueModalOpen, setIssueModalOpen] = useState(false)
  const [issueRepo, setIssueRepo] = useState('')
  const [issueTitle, setIssueTitle] = useState('')
  const [issueBody, setIssueBody] = useState('')
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false)

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
    enabled: false,
    retry: false,
  })

  const {
    data: priorities,
    isLoading: prioritiesLoading,
    isError: prioritiesError,
    refetch: refetchPriorities,
    isFetching: prioritiesFetching,
  } = useQuery({
    queryKey: ['github', 'priorities', orgId, connectedRepo],
    queryFn: () => githubService.getPriorities(orgId!),
    enabled: false,
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
      invalidateAll()
    },
  })

  const disconnectRepoMutation = useMutation({
    mutationFn: () => githubService.disconnectRepo(orgId!),
    onSuccess: () => {
      setConfirmingDisconnect(false)
      invalidateAll()
    },
  })

  const handleDisconnectClick = () => {
    if (confirmingDisconnect) {
      disconnectRepoMutation.mutate()
    } else {
      setConfirmingDisconnect(true)
    }
  }

  const createIssueMutation = useMutation({
    mutationFn: () => githubService.createIssue(orgId!, issueRepo, issueTitle, issueBody),
    onSuccess: () => {
      setIssueModalOpen(false)
      setIssueTitle('')
      setIssueBody('')
      invalidateAll()
    },
  })

  const filteredRepos = useMemo(() => {
    if (!repos) return []
    const q = search.trim().toLowerCase()
    if (!q) return repos
    return repos.filter(
      (r) => r.full_name.toLowerCase().includes(q) || (r.language ?? '').toLowerCase().includes(q)
    )
  }, [repos, search])

  const openIssueModal = (repoFullName?: string) => {
    setIssueRepo(repoFullName ?? connectedRepo ?? '')
    setIssueModalOpen(true)
  }

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <motion.div initial={reduceMotion ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">
            GitHub
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Repository intelligence and issue management
          </p>
        </div>
        <Button onClick={() => openIssueModal()} disabled={!connectedRepo && filteredRepos.length === 0}>
          <Plus size={15} />
          New issue
        </Button>
      </motion.div>

      {githubConnectResult === 'connected' && !connectedRepo && (
        <div className="rounded-lg border border-signal/30 bg-signal-dim px-4 py-3 text-sm text-text-primary" role="status">
          GitHub is connected. Choose a repository below to finish setup.
        </div>
      )}
      {githubConnectResult === 'connected' && connectedRepo && (
        <div className="rounded-lg border border-signal/30 bg-signal-dim px-4 py-3 text-sm text-text-primary" role="status">
          GitHub is connected to WorkForge.
        </div>
      )}
      {githubConnectResult === 'cancelled' && (
        <div className="rounded-lg border border-border bg-surface px-4 py-3 text-sm text-text-muted" role="status">
          GitHub connection was cancelled. You can connect whenever you&apos;re ready.
        </div>
      )}
      {githubConnectResult === 'failed' && (
        <ErrorBanner message="GitHub could not connect. Please try again." />
      )}


      <motion.div initial={reduceMotion ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: 0.05 }}>
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <GitBranch size={16} className="text-signal" />
            <h2 className="text-sm font-medium text-text-primary">Connected repository</h2>
          </div>
          {repoLoading ? (
            <Skeleton className="h-9 w-64" />
          ) : connectedRepo ? (
            <div className="flex items-center gap-2 text-sm text-text-primary">
              <CheckCircle2 size={14} className="text-signal" />
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
            <p className="text-sm text-text-faint mb-3">Choose a repository below to receive issue, push, and pull request events in WorkForge.</p>
          )}
          <div className="flex flex-wrap gap-2 mt-3">
            {connectedRepo && (
              <Button
                variant={confirmingDisconnect ? 'primary' : 'secondary'}
                onClick={handleDisconnectClick}
                onBlur={() => setConfirmingDisconnect(false)}
                loading={disconnectRepoMutation.isPending}
                className={confirmingDisconnect ? 'bg-alert! text-white!' : ''}
              >
                {confirmingDisconnect ? 'Confirm?' : 'Disconnect'}
              </Button>
            )}
          </div>
          {disconnectRepoMutation.isError && (
            <div className="mt-2">
              <ErrorBanner message="Failed to disconnect repository." />
            </div>
          )}
        </Card>
      </motion.div>


      <motion.div initial={reduceMotion ? false : { opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: 0.1 }} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-amber" />
              <h2 className="text-sm font-medium text-text-primary">AI summary</h2>
            </div>
            <button
              onClick={() => refetchSummary()}
              disabled={summaryFetching}
              className="text-text-faint hover:text-text-primary transition-colors"
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
          ) : summary === undefined ? (
            <div className="flex flex-col items-start gap-2">
              <p className="text-xs text-text-faint">
                Uses your AI quota — load on demand.
              </p>
              <Button variant="secondary" onClick={() => refetchSummary()}>
                Load AI summary
              </Button>
            </div>
          ) : (
            <FormattedAiText text={summary} />
          )}
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ListChecks size={16} className="text-signal" />
              <h2 className="text-sm font-medium text-text-primary">Prioritized issues</h2>
            </div>
            <button
              onClick={() => refetchPriorities()}
              disabled={prioritiesFetching || !connectedRepo}
              className="text-text-faint hover:text-text-primary transition-colors"
              title="Refresh"
            >
              <RefreshCw size={14} className={prioritiesFetching ? 'animate-spin' : ''} />
            </button>
          </div>
          {!connectedRepo ? (
            <p className="text-sm text-text-faint">Enable events for a repository to see its prioritized issues.</p>
          ) : prioritiesLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : prioritiesError ? (
            <ErrorBanner message="Couldn't load priorities. Try refreshing." />
          ) : priorities === undefined ? (
            <div className="flex flex-col items-start gap-2 mb-4">
              <p className="text-xs text-text-faint">
                Priorities for {connectedRepo}. Uses your AI quota — load on demand.
              </p>
              <Button variant="secondary" onClick={() => refetchPriorities()}>
                Load prioritized issues
              </Button>
            </div>
          ) : (
            <div className="mb-4"><FormattedAiText text={priorities} /></div>
          )}
        </Card>
      </motion.div>


      <motion.div initial={reduceMotion ? false : { opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: 0.15 }}>
        <Card className="p-5">
        <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
          <div>
            <h2 className="text-sm font-medium text-text-primary">
              Repositories {repos && <span className="text-text-faint">({repos.length})</span>}
            </h2>
            <p className="mt-1 text-xs text-text-faint">GitHub is authorized to list these repositories. Enable events on one repository to use it for WorkForge automations; this requires repository admin access.</p>
          </div>
          <div className="relative w-full max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-faint" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search repos..."
              className="w-full rounded-lg border border-border bg-surface pl-9 pr-3 py-2 text-sm text-text-primary placeholder:text-text-faint focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal"
            />
          </div>
        </div>

        {connectRepoMutation.isError && (
          <div className="mb-4">
            <ErrorBanner message={`${connectRepoMutation.variables}: ${apiErrorMessage(connectRepoMutation.error, 'Could not enable events for this repository. Check your GitHub permissions and try again.')}`} />
          </div>
        )}

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
          <div className="divide-y divide-border">
            {filteredRepos.map((repo: GitHubRepo, index) => (
              <motion.div key={repo.id} initial={reduceMotion ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.24, delay: Math.min(index * 0.035, 0.25) }} whileHover={reduceMotion ? undefined : { x: 3 }} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 py-3">
                <div className="min-w-0 flex-1">
                  <a href={repo.html_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-text-primary hover:underline flex items-center gap-1 w-fit"
                    >
                    {repo.full_name}
                    <ExternalLink size={11} />
                  </a>
                  {repo.description && (
                    <p className="text-xs text-text-faint truncate mt-0.5 max-w-md">
                      {repo.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {repo.language && <Badge tone="neutral">{repo.language}</Badge>}
                  {repo.open_issues_count > 0 && (
                    <Badge tone="amber">{repo.open_issues_count} open</Badge>
                  )}
                  <Button
                    variant={connectedRepo === repo.full_name ? 'secondary' : 'primary'}
                    disabled={connectedRepo === repo.full_name || connectRepoMutation.isPending}
                    loading={connectRepoMutation.isPending && connectRepoMutation.variables === repo.full_name}
                    onClick={() => connectRepoMutation.mutate(repo.full_name)}
                  >
                    {connectedRepo === repo.full_name ? 'Events enabled' : 'Enable events'}
                  </Button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
        </Card>
      </motion.div>


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
            <label className="text-sm font-medium text-text-muted">Description</label>
            <textarea
              value={issueBody}
              onChange={(e) => setIssueBody(e.target.value)}
              rows={4}
              placeholder="Optional description"
              className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-text-primary placeholder:text-text-faint focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal resize-none"
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
