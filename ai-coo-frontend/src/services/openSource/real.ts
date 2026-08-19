import { apiClient } from '@/api/client'
import type {
  OSIssueDetail, OSIssueListResponse, OSRepoDetail, OSRepoListResponse,
  OpenSourceService, RepoFilters,
} from './types'

export const realOpenSourceService: OpenSourceService = {
  listIssues: (orgId, filters) =>
    apiClient
      .get<OSIssueListResponse>('/open-source/issues', {
        params: {
          org_id: orgId,
          language: filters.language,
          label: filters.label,
          unassigned_only: filters.unassignedOnly,
          search: filters.search,
          sort: filters.sort,
          org: filters.org,
          repo: filters.repo,
          page: filters.page,
          per_page: filters.perPage,
        },
      })
      .then((r) => r.data),

  getIssue: (orgId, owner, repo, issueNumber) =>
    apiClient
      .get<OSIssueDetail>(`/open-source/issues/${owner}/${repo}/${issueNumber}`, { params: { org_id: orgId } })
      .then((r) => r.data),

  listRepositories: (orgId, filters: RepoFilters) =>
    apiClient
      .get<OSRepoListResponse>('/open-source/repositories', {
        params: {
          org_id: orgId,
          language: filters.language,
          topic: filters.topic,
          search: filters.search,
          sort: filters.sort,
          org: filters.org,
          page: filters.page,
          per_page: filters.perPage,
        },
      })
      .then((r) => r.data),

  getRepository: (orgId, owner, repo) =>
    apiClient
      .get<OSRepoDetail>(`/open-source/repositories/${owner}/${repo}`, { params: { org_id: orgId } })
      .then((r) => r.data),

  recordOpportunitySelected: (organizationId, resourceType, repoFullName, issueNumber, title) =>
    apiClient
      .post('/open-source/opportunity-selected', {
        organization_id: organizationId,
        resource_type: resourceType,
        repo_full_name: repoFullName,
        issue_number: issueNumber,
        title,
      })
      .then(() => undefined),
}
