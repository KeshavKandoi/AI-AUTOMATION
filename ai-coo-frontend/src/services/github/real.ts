import { apiClient } from '@/api/client'
import type {
  ConnectRepoResult,
  CreateIssueResult,
  CreateTasksFromPrioritiesResult,
  GitHubRepo,
  GitHubService,
} from './types'

export const realGitHubService: GitHubService = {
  getConnectedRepo: (orgId) =>
    apiClient
      .get<{ repo: string | null }>('/github/connected-repo', { params: { org_id: orgId } })
      .then((r) => r.data.repo),

  listRepos: (orgId) =>
    apiClient.get<GitHubRepo[]>('/github/repos', { params: { org_id: orgId } }).then((r) => r.data),

  getSummary: (orgId) =>
    apiClient
      .get<{ summary: string }>('/github/summary', { params: { org_id: orgId } })
      .then((r) => r.data.summary),

  getPriorities: (orgId) =>
    apiClient
      .get<{ priorities: string }>('/planner/priorities', { params: { org_id: orgId } })
      .then((r) => r.data.priorities),

  createIssue: (orgId, repoFullName, title, body) =>
    apiClient
      .post<CreateIssueResult>('/github/create-issue', undefined, {
        params: { org_id: orgId, repo_full_name: repoFullName, title, body },
      })
      .then((r) => r.data),

  connectRepo: (orgId, repoFullName) =>
    apiClient
      .post<ConnectRepoResult>('/github/connect-repo', undefined, {
        params: { org_id: orgId, repo_full_name: repoFullName },
      })
      .then((r) => r.data),

  createTasksFromPriorities: (orgId) =>
    apiClient
      .get<CreateTasksFromPrioritiesResult>('/tasks/create-from-priorities', { params: { org_id: orgId } })
      .then((r) => r.data),
}
