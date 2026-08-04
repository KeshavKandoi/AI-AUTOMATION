import { apiClient } from '@/api/client'
import type {
  BranchOption,
  CommitJob,
  CommitJobFile,
  CommitJobRun,
  CommitJobWithRuns,
  CommitSchedulerService,
  RepoOption,
} from './types'

export const realCommitSchedulerService: CommitSchedulerService = {
  listJobs: (orgId) =>
    apiClient.get<CommitJob[]>('/commit-jobs', { params: { org_id: orgId } }).then((r) => r.data),

  getJob: (jobId, orgId) =>
    apiClient
      .get<CommitJobWithRuns>(`/commit-jobs/${jobId}`, { params: { org_id: orgId } })
      .then((r) => r.data),

  createJob: (payload) =>
    apiClient
      .post<{ status: string; job: CommitJob }>('/commit-jobs', payload)
      .then((r) => r.data.job),

  updateJob: (jobId, orgId, payload) =>
    apiClient
      .patch<{ status: string; job: CommitJob }>(`/commit-jobs/${jobId}`, payload, {
        params: { org_id: orgId },
      })
      .then((r) => r.data.job),

  deleteJob: (jobId, orgId) =>
    apiClient
      .delete(`/commit-jobs/${jobId}`, { params: { org_id: orgId } })
      .then(() => undefined),

  runNow: (jobId, orgId) =>
    apiClient
      .post<{ status: string; run: CommitJobRun }>(
        `/commit-jobs/${jobId}/run-now`,
        undefined,
        { params: { org_id: orgId } }
      )
      .then((r) => r.data.run),

  listRepos: (orgId) =>
    apiClient
      .get<RepoOption[]>('/commit-jobs/meta/repos', { params: { org_id: orgId } })
      .then((r) => r.data),

  listBranches: (orgId, repoFullName) =>
    apiClient
      .get<BranchOption[]>('/commit-jobs/meta/branches', {
        params: { org_id: orgId, repo_full_name: repoFullName },
      })
      .then((r) => r.data),

  addFiles: (jobId, orgId, files) =>
    apiClient
      .post<{ status: string; files: CommitJobFile[] }>(
        `/commit-jobs/${jobId}/files`,
        files,
        { params: { org_id: orgId } }
      )
      .then((r) => r.data.files),

  listFiles: (jobId, orgId) =>
    apiClient
      .get<CommitJobFile[]>(`/commit-jobs/${jobId}/files`, { params: { org_id: orgId } })
      .then((r) => r.data),

  deleteFile: (jobId, orgId, fileId) =>
    apiClient
      .delete(`/commit-jobs/${jobId}/files/${fileId}`, { params: { org_id: orgId } })
      .then(() => undefined),
}
