export interface OSAuthor {
  login: string
  avatar_url: string | null
}

export interface OSIssueSummary {
  repo_full_name: string
  number: number
  title: string
  html_url: string
  state: string
  labels: string[]
  comments_count: number
  created_at: string
  updated_at: string
  author: OSAuthor
}

export interface OSIssueListResponse {
  items: OSIssueSummary[]
  total_count: number
  page: number
  per_page: number
}

export interface OSIssueComment {
  id: number
  author: OSAuthor
  body: string
  created_at: string
}

export interface OSIssueDetail {
  repo_full_name: string
  number: number
  title: string
  body: string | null
  html_url: string
  state: string
  labels: string[]
  author: OSAuthor
  assignee: OSAuthor | null
  comments_count: number
  created_at: string
  updated_at: string
  comments: OSIssueComment[]
}

export interface OSRepoSummary {
  full_name: string
  name: string
  description: string | null
  html_url: string
  language: string | null
  topics: string[]
  stargazers_count: number
  open_issues_count: number
  default_branch: string
  updated_at: string
}

export interface OSRepoListResponse {
  items: OSRepoSummary[]
  total_count: number
  page: number
  per_page: number
}

export interface OSRepoDetail extends OSRepoSummary {
  forks_count: number
  license_name: string | null
  homepage: string | null
}

export type IssueSort = 'updated' | 'created' | 'comments'
export type RepoSort = 'stars' | 'updated' | 'forks'

export interface IssueFilters {
  language?: string
  label?: string
  unassignedOnly?: boolean
  search?: string
  sort?: IssueSort
  org?: string
  repo?: string
  page?: number
  perPage?: number
}

export interface RepoFilters {
  language?: string
  topic?: string
  search?: string
  sort?: RepoSort
  org?: string
  page?: number
  perPage?: number
}

export interface OpenSourceService {
  listIssues(orgId: string, filters: IssueFilters): Promise<OSIssueListResponse>
  getIssue(orgId: string, owner: string, repo: string, issueNumber: number): Promise<OSIssueDetail>
  listRepositories(orgId: string, filters: RepoFilters): Promise<OSRepoListResponse>
  getRepository(orgId: string, owner: string, repo: string): Promise<OSRepoDetail>
  recordOpportunitySelected(
    organizationId: string,
    resourceType: 'issue' | 'repository',
    repoFullName: string,
    issueNumber?: number,
    title?: string
  ): Promise<void>
}

export function splitRepoFullName(repoFullName: string): [string, string] {
  const idx = repoFullName.indexOf('/')
  return [repoFullName.slice(0, idx), repoFullName.slice(idx + 1)]
}
