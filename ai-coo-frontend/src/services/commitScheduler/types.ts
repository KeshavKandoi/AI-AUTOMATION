export type Frequency = 'daily' | 'every_2_days' | 'weekdays' | 'custom'
export type JobStatus = 'active' | 'paused' | 'completed' | 'cancelled'
export type RunStatus = 'pending' | 'success' | 'failed' | 'skipped'
export type JobMode = 'scheduled' | 'guard'

export interface CommitJobFile {
  id?: string
  job_id?: string
  target_date: string | null
  folder_path: string
  file_name: string
  content: string | null
}

export interface CommitJob {
  id: string
  organization_id: string
  provider: string
  repo_full_name: string
  branch: string
  folder_path: string | null
  file_name: string | null
  file_content: string | null
  commit_message: string
  start_date: string
  end_date: string
  frequency: Frequency
  custom_dates: string[] | null
  mode: JobMode
  guard_cutoff_time: string
  use_pr: boolean
  status: JobStatus
  created_at: string
  updated_at: string
  files?: CommitJobFile[]
}

export interface CommitJobRun {
  id: string
  job_id: string
  run_date: string
  status: RunStatus
  commit_sha: string | null
  commit_url: string | null
  error_message: string | null
  executed_at: string
}

export interface CommitJobWithRuns extends CommitJob {
  runs: CommitJobRun[]
}

export interface RepoOption {
  full_name: string
  name: string
  default_branch: string
}

export interface BranchOption {
  name: string
}

export interface CreateJobPayload {
  organization_id: string
  provider?: string
  repo_full_name: string
  branch?: string
  folder_path?: string
  file_name?: string
  file_content?: string
  commit_message: string
  start_date: string
  end_date: string
  frequency?: Frequency
  custom_dates?: string[]
  mode?: JobMode
  guard_cutoff_time?: string
  use_pr?: boolean
  files?: Omit<CommitJobFile, 'id' | 'job_id'>[]
}

export interface UpdateJobPayload {
  branch?: string
  folder_path?: string
  file_name?: string
  file_content?: string
  commit_message?: string
  start_date?: string
  end_date?: string
  frequency?: Frequency
  custom_dates?: string[]
  status?: JobStatus
}

export interface CommitSchedulerService {
  listJobs(orgId: string): Promise<CommitJob[]>
  getJob(jobId: string, orgId: string): Promise<CommitJobWithRuns>
  createJob(payload: CreateJobPayload): Promise<CommitJob>
  updateJob(jobId: string, orgId: string, payload: UpdateJobPayload): Promise<CommitJob>
  deleteJob(jobId: string, orgId: string): Promise<void>
  runNow(jobId: string, orgId: string): Promise<CommitJobRun>
  listRepos(orgId: string): Promise<RepoOption[]>
  listBranches(orgId: string, repoFullName: string): Promise<BranchOption[]>
  addFiles(jobId: string, orgId: string, files: Omit<CommitJobFile, 'id' | 'job_id'>[]): Promise<CommitJobFile[]>
  listFiles(jobId: string, orgId: string): Promise<CommitJobFile[]>
  deleteFile(jobId: string, orgId: string, fileId: string): Promise<void>
}
