// Matches backend/job_hunter/routes.py exactly. Every route derives the
// organization from the authenticated JWT (see get_current_org_id) — none
// of these routes accept or read an org_id query param, so we deliberately
// don't send one (unlike some other services in this app that append an
// org_id param the backend silently ignores).
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
  NoteOut,
  PreferencesResponse,
  ProviderHealthResponse,
  ReminderOut,
  SearchTriggerResponse,
} from './types'

export const realJobHunterService = {
  // Preferences / onboarding
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

  // Jobs
  listJobs: (limit = 50, offset = 0, filters: JobListFilters = {}) =>
    apiClient
      .get<JobListResponse>('/job-hunter/jobs', { params: { limit, offset, ...filters } })
      .then((r) => r.data),

  getJob: (jobId: string) =>
    apiClient.get<JobOut>(`/job-hunter/jobs/${jobId}`).then((r) => r.data),

  // Applications
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

  // Notes
  addNote: (applicationId: string, content: string) =>
    apiClient
      .post<{ status: string; note: NoteOut }>(`/job-hunter/applications/${applicationId}/notes`, {
        content,
      })
      .then((r) => r.data.note),

  // Attachments
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

  // Reminders
  createReminder: (applicationId: string, remindAt: string, note?: string) =>
    apiClient
      .post<{ status: string; reminder: ReminderOut }>(
        `/job-hunter/applications/${applicationId}/reminders`,
        { remind_at: remindAt, note }
      )
      .then((r) => r.data.reminder),

  // Search trigger — backend now returns immediately (202) and runs the
  // sweep in the background via the existing scheduler, since a full
  // sweep can take several minutes and was previously blocking the
  // request until Render's proxy timed it out. No jobs_found/jobs_new
  // counts are available synchronously anymore.
  runSearchNow: () =>
    apiClient
      .post<SearchTriggerResponse>('/job-hunter/search/run-now')
      .then((r) => r.data),

  // Provider health
  getProviderHealth: () =>
    apiClient.get<ProviderHealthResponse>('/job-hunter/providers/health').then((r) => r.data),
}
