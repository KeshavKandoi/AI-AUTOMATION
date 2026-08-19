export type PRView =
  | 'all' | 'mine' | 'in_my_repos' | 'needs_review'
  | 'waiting_review' | 'changes_requested' | 'approved' | 'merged' | 'closed'

export interface PRAuthor {
  login: string
  avatar_url: string | null
}

export interface PRSummary {
  repo_full_name: string
  number: number
  title: string
  author: PRAuthor
  state: string
  is_draft: boolean
  is_merged: boolean
  html_url: string
  base_branch: string | null
  head_branch: string | null
  labels: string[]
  comments_count: number
  created_at: string
  updated_at: string
}

export interface PRListResponse {
  items: PRSummary[]
  total_count: number
  page: number
  per_page: number
}

export interface PRReview {
  id: number
  author: PRAuthor
  state: string
  body: string | null
  submitted_at: string | null
}

export interface PRComment {
  id: number
  author: PRAuthor
  body: string
  created_at: string
  path: string | null
}

export interface PRCommit {
  sha: string
  message: string
  author_name: string | null
  authored_at: string | null
}

export interface PRFile {
  filename: string
  status: string
  additions: number
  deletions: number
  changes: number
}

export interface PRCheckRun {
  name: string
  status: string
  conclusion: string | null
  html_url: string | null
}

export interface PRDetail {
  repo_full_name: string
  number: number
  title: string
  body: string | null
  author: PRAuthor
  state: string
  is_draft: boolean
  is_merged: boolean
  mergeable: boolean | null
  mergeable_state: string | null
  html_url: string
  base_branch: string
  head_branch: string
  additions: number
  deletions: number
  changed_files: number
  commits_count: number
  labels: string[]
  created_at: string
  updated_at: string
  merged_at: string | null
  reviews: PRReview[]
  comments: PRComment[]
  commits: PRCommit[]
  files: PRFile[]
  checks: PRCheckRun[]
  review_decision: 'approved' | 'changes_requested' | 'review_required' | 'none' | string
}

export type MergeMethod = 'merge' | 'squash' | 'rebase'

export interface PullRequestsService {
  listPullRequests(
    orgId: string,
    view: PRView,
    repo?: string,
    author?: string,
    search?: string,
    page?: number,
    perPage?: number
  ): Promise<PRListResponse>
  getPullRequest(orgId: string, owner: string, repo: string, prNumber: number): Promise<PRDetail>
  getSummary(orgId: string, owner: string, repo: string, prNumber: number): Promise<string>
  approvePullRequest(orgId: string, owner: string, repo: string, prNumber: number, body?: string): Promise<unknown>
  requestChanges(orgId: string, owner: string, repo: string, prNumber: number, body: string): Promise<unknown>
  commentOnPullRequest(orgId: string, owner: string, repo: string, prNumber: number, body: string): Promise<unknown>
  mergePullRequest(orgId: string, owner: string, repo: string, prNumber: number, mergeMethod: MergeMethod): Promise<unknown>
  closePullRequest(orgId: string, owner: string, repo: string, prNumber: number): Promise<unknown>
}

// repo_full_name from GitHub is always "owner/repo" — split on the first slash only,
// since repo names themselves never contain a slash.
export function splitRepoFullName(repoFullName: string): [string, string] {
  const idx = repoFullName.indexOf('/')
  return [repoFullName.slice(0, idx), repoFullName.slice(idx + 1)]
}
