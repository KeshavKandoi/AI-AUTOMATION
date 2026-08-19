import { apiClient } from '@/api/client'
import type {
  MergeMethod,
  PRDetail,
  PRListResponse,
  PullRequestsService,
} from './types'

export const realPullRequestsService: PullRequestsService = {
  listPullRequests: (orgId, view, repo, author, search, page = 1, perPage = 30) =>
    apiClient
      .get<PRListResponse>('/pull-requests', {
        params: { org_id: orgId, view, repo, author, search, page, per_page: perPage },
      })
      .then((r) => r.data),

  getPullRequest: (orgId, owner, repo, prNumber) =>
    apiClient
      .get<PRDetail>(`/pull-requests/${owner}/${repo}/${prNumber}`, { params: { org_id: orgId } })
      .then((r) => r.data),

  getSummary: (orgId, owner, repo, prNumber) =>
    apiClient
      .get<{ summary: string }>(`/pull-requests/${owner}/${repo}/${prNumber}/summary`, {
        params: { org_id: orgId },
      })
      .then((r) => r.data.summary),

  approvePullRequest: (orgId, owner, repo, prNumber, body) =>
    apiClient
      .post(`/pull-requests/${owner}/${repo}/${prNumber}/approve`, { body }, { params: { org_id: orgId } })
      .then((r) => r.data),

  requestChanges: (orgId, owner, repo, prNumber, body) =>
    apiClient
      .post(`/pull-requests/${owner}/${repo}/${prNumber}/request-changes`, { body }, { params: { org_id: orgId } })
      .then((r) => r.data),

  commentOnPullRequest: (orgId, owner, repo, prNumber, body) =>
    apiClient
      .post(`/pull-requests/${owner}/${repo}/${prNumber}/comment`, { body }, { params: { org_id: orgId } })
      .then((r) => r.data),

  mergePullRequest: (orgId, owner, repo, prNumber, mergeMethod: MergeMethod) =>
    apiClient
      .post(`/pull-requests/${owner}/${repo}/${prNumber}/merge`, { merge_method: mergeMethod }, { params: { org_id: orgId } })
      .then((r) => r.data),

  closePullRequest: (orgId, owner, repo, prNumber) =>
    apiClient
      .post(`/pull-requests/${owner}/${repo}/${prNumber}/close`, undefined, { params: { org_id: orgId } })
      .then((r) => r.data),
}
