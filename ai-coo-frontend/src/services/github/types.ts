export interface GitHubRepo {
  id: number
  name: string
  full_name: string
  private: boolean
  html_url: string
  description: string | null
  language: string | null
  open_issues_count: number
  updated_at: string
}

export interface CreateIssueResult {
  status: string
  issue_number: number
  url: string
}

export interface ConnectRepoResult {
  status: string
  repo: string
  webhook_id?: number
}

export interface CreateTasksFromPrioritiesResult {
  tasks_created: number
  tasks: unknown[]
  message?: string
}

export interface DisconnectRepoResult {
  status: string
  repo: string
}

export interface GitHubService {
  getConnectedRepo(orgId: string): Promise<string | null>
  listRepos(orgId: string): Promise<GitHubRepo[]>
  getSummary(orgId: string): Promise<string>
  getPriorities(orgId: string): Promise<string>
  createIssue(orgId: string, repoFullName: string, title: string, body: string): Promise<CreateIssueResult>
  connectRepo(orgId: string, repoFullName: string): Promise<ConnectRepoResult>
  disconnectRepo(orgId: string): Promise<DisconnectRepoResult>
  createTasksFromPriorities(orgId: string): Promise<CreateTasksFromPrioritiesResult>
}
