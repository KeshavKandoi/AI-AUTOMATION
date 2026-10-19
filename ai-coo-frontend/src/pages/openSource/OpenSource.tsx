import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { AlertCircle, GitFork, Search, Star, ExternalLink, MessageSquare } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { openSourceService, splitRepoFullName, type OSIssueSummary, type OSRepoSummary, type IssueSort, type RepoSort } from '@/services/openSource'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Badge from '@/components/ui/Badge'
import OpportunityDetailDrawer from './OpportunityDetailDrawer'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-alert-dim bg-alert-dim px-3 py-2 text-xs text-alert">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

type Tab = 'issues' | 'repositories'

const QUICK_LABELS = [
  { label: 'Good first issue', value: 'good first issue' },
  { label: 'Help wanted', value: 'help wanted' },
]

export default function OpenSource() {
  const reduceMotion = useReducedMotion()
  const orgId = useAuthStore((s) => s.user?.organization_id)

  const [tab, setTab] = useState<Tab>('issues')
  const [search, setSearch] = useState('')
  const [language, setLanguage] = useState('')
  const [org, setOrg] = useState('')
  const [topic, setTopic] = useState('')
  const [quickLabel, setQuickLabel] = useState('')
  const [unassignedOnly, setUnassignedOnly] = useState(true)
  const [issueSort, setIssueSort] = useState<IssueSort>('updated')
  const [repoSort, setRepoSort] = useState<RepoSort>('stars')

  const [selectedIssue, setSelectedIssue] = useState<{ owner: string; repo: string; number: number } | null>(null)
  const [selectedRepo, setSelectedRepo] = useState<{ owner: string; repo: string } | null>(null)
  const [repoFilter, setRepoFilter] = useState('')

  const viewIssuesForRepo = (repoFullName: string) => {
    setRepoFilter(repoFullName)
    setOrg('')
    setSearch('')
    setTab('issues')
  }

  const { data: issueData, isLoading: issuesLoading, isFetching: issuesFetching, isError: issuesError } = useQuery({
    queryKey: ['open-source', 'issues', orgId, language, org, repoFilter, quickLabel, unassignedOnly, search, issueSort],
    queryFn: () =>
      openSourceService.listIssues(orgId!, {
        language: language || undefined,
        org: org || undefined,
        repo: repoFilter || undefined,
        label: quickLabel || undefined,
        unassignedOnly,
        search: search || undefined,
        sort: issueSort,
      }),
    enabled: !!orgId && tab === 'issues',
  })

  const { data: repoData, isLoading: reposLoading, isFetching: reposFetching, isError: reposError } = useQuery({
    queryKey: ['open-source', 'repositories', orgId, language, org, topic, search, repoSort],
    queryFn: () =>
      openSourceService.listRepositories(orgId!, {
        language: language || undefined,
        org: org || undefined,
        topic: topic || undefined,
        search: search || undefined,
        sort: repoSort,
      }),
    enabled: !!orgId && tab === 'repositories',
  })

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto flex flex-col gap-6">
      <motion.header
        initial={reduceMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.35 }}
        className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-signal-dim/80 via-surface to-surface px-5 py-6 sm:px-7"
      >
        <div aria-hidden="true" className="pointer-events-none absolute -right-12 -top-24 h-56 w-56 rounded-full bg-signal/8 blur-3xl" />
        <div className="relative flex items-center gap-4">
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-signal/20 bg-void/60 text-signal">
            <GitFork size={21} />
          </span>
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-signal">Explore & contribute</p>
            <h1 className="font-display text-2xl font-semibold text-text-primary">Open Source</h1>
            <p className="mt-1 text-sm text-text-muted">Find repositories and issues that fit your interests.</p>
          </div>
        </div>
      </motion.header>

      <motion.div initial={reduceMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : 0.28, delay: reduceMotion ? 0 : 0.04 }} className="flex gap-1 border-b border-border" role="group" aria-label="Open source results">
        <button
          type="button"
          aria-pressed={tab === 'issues'}
          onClick={() => setTab('issues')}
          className={`relative px-4 py-2 text-sm transition-colors ${tab === 'issues' ? 'font-medium text-signal' : 'text-text-muted hover:text-text-primary'}`}
        >
          Issues
          {tab === 'issues' && <motion.span layoutId="open-source-tab" className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-signal" />}
        </button>
        <button
          type="button"
          aria-pressed={tab === 'repositories'}
          onClick={() => setTab('repositories')}
          className={`relative px-4 py-2 text-sm transition-colors ${tab === 'repositories' ? 'font-medium text-signal' : 'text-text-muted hover:text-text-primary'}`}
        >
          Repositories
          {tab === 'repositories' && <motion.span layoutId="open-source-tab" className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-signal" />}
        </button>
      </motion.div>

      <motion.div initial={reduceMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : 0.28, delay: reduceMotion ? 0 : 0.08 }} className="flex flex-wrap items-center gap-2 rounded-2xl border border-border bg-surface/65 p-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-faint" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={tab === 'issues' ? 'Search issues...' : 'Search repositories...'}
            className="w-56 rounded-lg border border-border bg-surface pl-8 pr-3 py-2 text-sm text-text-primary placeholder:text-text-faint focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal"
          />
        </div>

        <input
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          placeholder="Language (e.g. TypeScript)"
          className="w-44 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-faint focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal"
        />

        <input
          value={org}
          onChange={(e) => setOrg(e.target.value)}
          placeholder="Company / org (e.g. facebook)"
          className="w-52 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-faint focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal"
        />

        {tab === 'repositories' && (
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Topic (e.g. react)"
            className="w-40 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-faint focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal"
          />
        )}

        {tab === 'issues' ? (
          <select
            value={issueSort}
            onChange={(e) => setIssueSort(e.target.value as IssueSort)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-signal"
          >
            <option value="updated">Recently updated</option>
            <option value="created">Newest</option>
            <option value="comments">Most discussed</option>
          </select>
        ) : (
          <select
            value={repoSort}
            onChange={(e) => setRepoSort(e.target.value as RepoSort)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-signal"
          >
            <option value="stars">Most stars</option>
            <option value="updated">Recently updated</option>
            <option value="forks">Most forks</option>
          </select>
        )}
        {((tab === 'issues' && issuesFetching && !issuesLoading) || (tab === 'repositories' && reposFetching && !reposLoading)) && (
          <span className="text-xs text-text-faint">Updating...</span>
        )}
      </motion.div>

      {tab === 'issues' && repoFilter && (
        <div className="flex items-center gap-2">
          <Badge tone="signal">Filtered to {repoFilter}</Badge>
          <button
            onClick={() => setRepoFilter('')}
            className="text-xs text-text-faint hover:text-text-primary underline"
          >
            Clear
          </button>
        </div>
      )}

      {tab === 'issues' && (
        <div className="flex flex-wrap items-center gap-2">
          {QUICK_LABELS.map((q) => (
            <button
              key={q.value}
              onClick={() => setQuickLabel(quickLabel === q.value ? '' : q.value)}
              className={
                quickLabel === q.value
                  ? 'text-xs rounded-full px-3 py-1.5 bg-signal-dim text-signal border border-signal'
                  : 'text-xs rounded-full px-3 py-1.5 bg-surface text-text-muted border border-border hover:border-border-hover'
              }
            >
              {q.label}
            </button>
          ))}
          <button
            onClick={() => setUnassignedOnly((v) => !v)}
            className={
              unassignedOnly
                ? 'text-xs rounded-full px-3 py-1.5 bg-signal-dim text-signal border border-signal'
                : 'text-xs rounded-full px-3 py-1.5 bg-surface text-text-muted border border-border hover:border-border-hover'
            }
          >
            Unassigned only
          </button>
        </div>
      )}

      {tab === 'issues' ? (
        issuesLoading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
          </div>
        ) : issuesError ? (
          <ErrorBanner message="Couldn't load issues. Check your GitHub connection, or try disabling ad blockers/privacy extensions for this site." />
        ) : !issueData || issueData.items.length === 0 ? (
          <Card className="p-8">
            <EmptyState
              icon={MessageSquare}
              title="No issues match your filters"
              description={
                unassignedOnly
                  ? "Try turning off \"Unassigned only\" — popular repos often have their good-first-issues already claimed."
                  : "Try a different language, org, or clearing filters."
              }
            />
          </Card>
        ) : (
        <motion.div layout className={`flex flex-col gap-3 transition-opacity ${issuesFetching ? 'opacity-50' : ''}`}>
          <AnimatePresence mode="popLayout" initial={false}>
            {issueData.items.map((issue: OSIssueSummary, index) => (
              <motion.div key={`${issue.repo_full_name}#${issue.number}`} layout initial={reduceMotion ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={reduceMotion ? undefined : { opacity: 0, y: -8 }} transition={{ duration: reduceMotion ? 0 : 0.25, delay: reduceMotion ? 0 : Math.min(index * 0.035, 0.2) }} whileHover={reduceMotion ? undefined : { y: -2 }}>
              <Card className="p-5 transition-colors hover:border-border-hover">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={() => {
                          const [owner, repo] = splitRepoFullName(issue.repo_full_name)
                          setSelectedIssue({ owner, repo, number: issue.number })
                        }}
                        className="text-sm font-medium text-text-primary hover:underline text-left"
                      >
                        {issue.title}
                      </button>
                      {issue.labels.slice(0, 3).map((l) => <Badge key={l} tone="neutral">{l}</Badge>)}
                    </div>
                    <p className="text-xs text-text-muted mt-1">
                      {issue.repo_full_name} · #{issue.number} · by {issue.author.login}
                    </p>
                    <p className="text-[11px] text-text-faint mt-1">
                      updated {formatDistanceToNow(new Date(issue.updated_at), { addSuffix: true })}
                      {issue.comments_count > 0 && ` · ${issue.comments_count} comments`}
                    </p>
                  </div>
                  <a href={issue.html_url} target="_blank" rel="noreferrer" className="text-text-faint hover:text-text-primary transition-colors shrink-0" title="Open on GitHub">
                    <ExternalLink size={14} />
                  </a>
                </div>
              </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
        )
      ) : reposLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
        </div>
      ) : reposError ? (
        <ErrorBanner message="Couldn't load repositories. Check your GitHub connection, or try disabling ad blockers/privacy extensions for this site." />
      ) : !repoData || repoData.items.length === 0 ? (
        <Card className="p-8">
          <EmptyState icon={GitFork} title="No repositories match your filters" description="Try a different language, org, or topic." />
        </Card>
      ) : (
        <motion.div layout className={`flex flex-col gap-3 transition-opacity ${reposFetching ? 'opacity-50' : ''}`}>
          <AnimatePresence mode="popLayout" initial={false}>
          {repoData.items.map((repo: OSRepoSummary, index) => (
            <motion.div key={repo.full_name} layout initial={reduceMotion ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={reduceMotion ? undefined : { opacity: 0, y: -8 }} transition={{ duration: reduceMotion ? 0 : 0.25, delay: reduceMotion ? 0 : Math.min(index * 0.035, 0.2) }} whileHover={reduceMotion ? undefined : { y: -2 }}>
            <Card className="p-5 transition-colors hover:border-border-hover">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={() => {
                        const [owner, name] = splitRepoFullName(repo.full_name)
                        setSelectedRepo({ owner, repo: name })
                      }}
                      className="text-sm font-medium text-text-primary hover:underline text-left"
                    >
                      {repo.full_name}
                    </button>
                    {repo.language && <Badge tone="neutral">{repo.language}</Badge>}
                  </div>
                  {repo.description && (
                    <p className="text-xs text-text-muted mt-1 max-w-2xl">{repo.description}</p>
                  )}
                  <p className="text-[11px] text-text-faint mt-1 flex items-center gap-3">
                    <span className="flex items-center gap-1"><Star size={11} /> {repo.stargazers_count.toLocaleString()}</span>
                    <span>{repo.open_issues_count} open issues</span>
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    onClick={() => viewIssuesForRepo(repo.full_name)}
                    className="text-xs text-signal hover:underline"
                  >
                    View issues
                  </button>
                  <a href={repo.html_url} target="_blank" rel="noreferrer" className="text-text-faint hover:text-text-primary transition-colors" title="Open on GitHub">
                    <ExternalLink size={14} />
                  </a>
                </div>
              </div>
            </Card>
            </motion.div>
          ))}
          </AnimatePresence>
        </motion.div>
      )}

      <OpportunityDetailDrawer
        orgId={orgId ?? ''}
        issueTarget={selectedIssue}
        repoTarget={selectedRepo}
        onCloseIssue={() => setSelectedIssue(null)}
        onCloseRepo={() => setSelectedRepo(null)}
      />
    </div>
  )
}
