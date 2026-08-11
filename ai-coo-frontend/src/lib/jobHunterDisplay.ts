import type { ApplicationStatus } from '@/services/jobHunter'

type BadgeTone = 'signal' | 'alert' | 'amber' | 'neutral'

// Ordered left-to-right for the Kanban tracker — matches
// backend/job_hunter/schemas.py ApplicationStatus exactly. Do not add or
// reorder without checking the backend Literal type first.
export const APPLICATION_STATUSES: ApplicationStatus[] = [
  'saved',
  'applied',
  'assessment',
  'interview',
  'hr_round',
  'technical_round',
  'final_round',
  'offer',
  'rejected',
  'archived',
]

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: 'Saved',
  applied: 'Applied',
  assessment: 'Assessment',
  interview: 'Interview',
  hr_round: 'HR Round',
  technical_round: 'Technical Round',
  final_round: 'Final Round',
  offer: 'Offer',
  rejected: 'Rejected',
  archived: 'Archived',
}

export function getStatusLabel(status: ApplicationStatus | string): string {
  return STATUS_LABELS[status as ApplicationStatus] ?? status.replace(/_/g, ' ')
}

const STATUS_TONES: Record<ApplicationStatus, BadgeTone> = {
  saved: 'neutral',
  applied: 'neutral',
  assessment: 'amber',
  interview: 'amber',
  hr_round: 'amber',
  technical_round: 'amber',
  final_round: 'amber',
  offer: 'signal',
  rejected: 'alert',
  archived: 'neutral',
}

export function getStatusTone(status: ApplicationStatus | string): BadgeTone {
  return STATUS_TONES[status as ApplicationStatus] ?? 'neutral'
}

export function getEmploymentTypeLabel(type: string | null): string {
  if (!type) return ''
  const map: Record<string, string> = {
    full_time: 'Full-time',
    part_time: 'Part-time',
    internship: 'Internship',
    contract: 'Contract',
    freelance: 'Freelance',
  }
  return map[type] ?? type.replace(/_/g, ' ')
}

export function getWorkModeLabel(mode: string | null): string {
  if (!mode) return ''
  const map: Record<string, string> = {
    remote: 'Remote',
    hybrid: 'Hybrid',
    onsite: 'Onsite',
  }
  return map[mode] ?? mode.replace(/_/g, ' ')
}

export function formatSalaryRange(
  min: number | null,
  max: number | null,
  currency: string | null
): string | null {
  if (min == null && max == null) return null
  const cur = currency ?? ''
  if (min != null && max != null) return `${cur} ${min.toLocaleString()} – ${max.toLocaleString()}`
  if (min != null) return `${cur} ${min.toLocaleString()}+`
  return `Up to ${cur} ${max!.toLocaleString()}`
}
