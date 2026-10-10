// Mirrors backend/job_hunter/schemas.py exactly. Do not add fields not
// present on the backend response, and do not invent statuses/enums.

export type ExperienceLevel = 'student' | 'fresher' | 'experienced'

export type ApplicationStatus =
  | 'saved'
  | 'applied'
  | 'assessment'
  | 'interview'
  | 'hr_round'
  | 'technical_round'
  | 'final_round'
  | 'offer'
  | 'rejected'
  | 'archived'

export type AttachmentType =
  | 'resume'
  | 'cover_letter'
  | 'assignment'
  | 'interview_notes'
  | 'offer_letter'
  | 'other'

export type ActivitySource = 'user' | 'gmail' | 'system'
export type ReminderStatus = 'pending' | 'notified' | 'dismissed'

export interface ProjectHighlight {
  title: string
  description: string
}

// ---------------------------------------------------------------------------
// Preferences (onboarding)
// ---------------------------------------------------------------------------

export interface JobHunterPreferencesCreate {
  full_name: string
  email: string
  experience_level: ExperienceLevel
  years_of_experience?: number
  current_designation?: string
  current_company?: string
  employment_types: string[]
  work_modes: string[]
  desired_roles: string[]
  skills: string[]
  project_highlights: ProjectHighlight[]
  preferred_locations: string[]
  expected_salary_min?: number
  expected_salary_max?: number
  salary_currency?: string
}

export type JobHunterPreferencesUpdate = Partial<JobHunterPreferencesCreate>

export interface JobHunterPreferencesOut {
  id: string
  organization_id: string
  full_name: string
  email: string
  experience_level: string
  years_of_experience: number | null
  current_designation: string | null
  current_company: string | null
  employment_types: string[]
  work_modes: string[]
  desired_roles: string[]
  skills: string[]
  project_highlights: ProjectHighlight[]
  preferred_locations: string[]
  expected_salary_min: number | null
  expected_salary_max: number | null
  salary_currency: string | null
  onboarding_completed: boolean
  created_at: string
  updated_at: string
}

export interface PreferencesResponse {
  onboarding_completed: boolean
  preferences: JobHunterPreferencesOut | null
}

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

export interface JobSourceOut {
  id: string
  job_id: string
  platform: string
  platform_job_id: string | null
  platform_url: string
  discovered_at: string
}

export interface JobOut {
  id: string
  organization_id: string
  company_name: string
  job_title: string
  location: string | null
  work_mode: string | null
  employment_type: string | null
  experience_required: string | null
  salary_min: number | null
  salary_max: number | null
  salary_currency: string | null
  description: string | null
  responsibilities: string | null
  required_skills: string[]
  qualifications: string | null
  benefits: string | null
  company_info: string | null
  original_apply_url: string
  posted_at: string | null
  first_discovered_at: string
  last_seen_at: string
  sources: JobSourceOut[]
}

export interface JobListResponse {
  items: JobOut[]
  total: number
  limit: number
  offset: number
}

export interface JobListFilters {
  employment_type?: string
  work_mode?: string
  search?: string
  roles?: string[]
  skills?: string[]
}

export interface LastSyncStatus {
  last_synced_at: string | null
  status: string | null
  jobs_found: number | null
  jobs_new: number | null
}

// ---------------------------------------------------------------------------
// Applications
// ---------------------------------------------------------------------------

export interface ActivityOut {
  id: string
  application_id: string
  event_type: string
  summary: string
  metadata: Record<string, unknown>
  source: ActivitySource
  created_at: string
}

export interface NoteOut {
  id: string
  application_id: string
  content: string
  created_at: string
  updated_at: string
}

export interface AttachmentOut {
  id: string
  application_id: string
  file_name: string
  storage_path: string
  file_type: AttachmentType | string
  size_bytes: number | null
  created_at: string
}

export interface ReminderOut {
  id: string
  application_id: string
  organization_id: string
  remind_at: string
  note: string | null
  status: ReminderStatus
  created_at: string
}

// Bare row shape returned by create/update application (no nested job/notes/etc)
export interface ApplicationRow {
  id: string
  organization_id: string
  job_id: string
  status: ApplicationStatus
  applied_at: string | null
  created_at: string
  updated_at: string
}

// Full detail shape returned by GET /applications/{id}
export interface ApplicationDetail extends ApplicationRow {
  job: JobOut | null
  activity: ActivityOut[]
  notes: NoteOut[]
  attachments: AttachmentOut[]
  reminders: ReminderOut[]
}

// ---------------------------------------------------------------------------
// Provider health
// ---------------------------------------------------------------------------

export interface ProviderStatus {
  organization_id: string
  platform: string
  status: string
  is_healthy: boolean
  last_run_at: string | null
  jobs_found_last_run: number
  last_error: string | null
  last_success_at: string | null
  updated_at: string
}

export interface ProviderHealthResponse {
  providers: ProviderStatus[]
  unhealthy_count: number
  unhealthy_platforms: string[]
}

// ---------------------------------------------------------------------------
// Search run-now
// ---------------------------------------------------------------------------

// Backend now returns immediately (202) and runs the sweep in the
// background — no jobs_found/jobs_new here since they don't exist yet
// at request time. "already_running" means the existing staleness-aware
// has_running_search() guard blocked a duplicate/overlapping trigger.
export interface SearchTriggerResponse {
  status: 'started' | 'already_running'
}
