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
