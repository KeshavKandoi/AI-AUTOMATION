




import { apiClient } from '@/api/client'
import type {
  ApplicationDetail,
  ApplicationRow,
  ApplicationStatus,
  AttachmentOut,
  AttachmentType,
  JobHunterPreferencesCreate,
  JobHunterPreferencesUpdate,
  JobListFilters,
  JobListResponse,
  JobOut,
  LastSyncStatus,
  NoteOut,
  PreferencesResponse,
  ProviderHealthResponse,
  ReminderOut,
  SearchTriggerResponse,
} from './types'

export const realJobHunterService = {

  getPreferences: () =>
    apiClient.get<PreferencesResponse>('/job-hunter/preferences').then((r) => r.data),

  savePreferences: (payload: JobHunterPreferencesCreate) =>
    apiClient
      .post<{ status: string; preferences: PreferencesResponse['preferences'] }>(
        '/job-hunter/preferences',
        payload
      )
      .then((r) => r.data.preferences!),

  updatePreferences: (payload: JobHunterPreferencesUpdate) =>
    apiClient
      .patch<{ status: string; preferences: PreferencesResponse['preferences'] }>(
        '/job-hunter/preferences',
        payload
      )
      .then((r) => r.data.preferences!),


  listJobs: (limit = 50, offset = 0, filters: JobListFilters = {}) => {
    const { roles, skills, ...rest } = filters
    const params: Record<string, unknown> = { limit, offset, ...rest }
    if (roles && roles.length > 0) params.roles = roles.join(',')
    if (skills && skills.length > 0) params.skills = skills.join(',')
    return apiClient
      .get<JobListResponse>('/job-hunter/jobs', { params })
      .then((r) => r.data)
  },

  getJob: (jobId: string) =>
    apiClient.get<JobOut>(`/job-hunter/jobs/${jobId}`).then((r) => r.data),



  getLastSync: () =>
    apiClient.get<LastSyncStatus>('/job-hunter/search/last-sync').then((r) => r.data),


  listApplications: (status?: ApplicationStatus) =>
    apiClient
      .get<ApplicationRow[]>('/job-hunter/applications', { params: status ? { status } : {} })
      .then((r) => r.data),

  createApplication: (jobId: string, status: ApplicationStatus = 'saved') =>
    apiClient
      .post<{ status: string; application: ApplicationRow }>('/job-hunter/applications', {
        job_id: jobId,
        status,
      })
      .then((r) => r.data.application),

  deleteSavedJob: (applicationId: string) =>
    apiClient.delete(`/job-hunter/applications/${applicationId}`).then(() => undefined),

  getApplication: (applicationId: string) =>
    apiClient
      .get<ApplicationDetail>(`/job-hunter/applications/${applicationId}`)
      .then((r) => r.data),

  updateApplicationStatus: (applicationId: string, status: ApplicationStatus) =>
    apiClient
      .patch<{ status: string; application: ApplicationRow }>(
        `/job-hunter/applications/${applicationId}`,
        { status }
      )
      .then((r) => r.data.application),


  addNote: (applicationId: string, content: string) =>
    apiClient
      .post<{ status: string; note: NoteOut }>(`/job-hunter/applications/${applicationId}/notes`, {
        content,
      })
      .then((r) => r.data.note),


  addAttachment: (applicationId: string, file: File, fileType: AttachmentType) => {
    const form = new FormData()
    form.append('file_type', fileType)
    form.append('file', file)
    return apiClient
      .post<{ status: string; attachment: AttachmentOut }>(
        `/job-hunter/applications/${applicationId}/attachments`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      .then((r) => r.data.attachment)
  },

  getAttachmentDownloadUrl: (applicationId: string, attachmentId: string) =>
    apiClient
      .get<{ download_url: string }>(
        `/job-hunter/applications/${applicationId}/attachments/${attachmentId}/download`
      )
      .then((r) => r.data.download_url),

  deleteAttachment: (applicationId: string, attachmentId: string) =>
    apiClient
      .delete(`/job-hunter/applications/${applicationId}/attachments/${attachmentId}`)
      .then(() => undefined),


  createReminder: (applicationId: string, remindAt: string, note?: string) =>
    apiClient
      .post<{ status: string; reminder: ReminderOut }>(
        `/job-hunter/applications/${applicationId}/reminders`,
        { remind_at: remindAt, note }
      )
      .then((r) => r.data.reminder),






  runSearchNow: () =>
    apiClient
      .post<SearchTriggerResponse>('/job-hunter/search/run-now')
      .then((r) => r.data),


  getProviderHealth: () =>
    apiClient.get<ProviderHealthResponse>('/job-hunter/providers/health').then((r) => r.data),
}
