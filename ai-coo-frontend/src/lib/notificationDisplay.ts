// Reuses the audit_logs module icon/label mapping since notifications share
// the same free-text `module` vocabulary (tasks, github, gmail, calendar,
// workflows, commit_scheduler, memory, integrations, system, auth) — no
// need to duplicate that lookup table here.
export { getModuleIcon, getModuleLabel } from './auditLogDisplay'

type BadgeTone = 'signal' | 'alert' | 'amber' | 'neutral'

export function getPriorityTone(priority: string | null): BadgeTone {
  switch (priority) {
    case 'urgent':
      return 'alert'
    case 'high':
      return 'amber'
    case 'normal':
      return 'signal'
    default:
      return 'neutral'
  }
}
