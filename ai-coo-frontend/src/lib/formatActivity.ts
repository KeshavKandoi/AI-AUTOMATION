import type { AuditLog } from '@/types/audit'

export function formatActivity(log: AuditLog): string {
  const d = log.details ?? {}
  switch (log.action) {
    case 'task_created':
      return `Task created: ${d.title ?? 'Untitled'}`
    case 'task_approved':
      return `Task approved: ${d.title ?? 'Untitled'}`
    case 'task_rejected':
      return `Task rejected: ${d.title ?? 'Untitled'}`
    case 'github_issue_created':
      return `GitHub issue opened`
    case 'email_sent':
      return `Email sent`
    case 'calendar_event_created':
      return `Calendar event created`
    case 'missed_event_recovered':
      return `Missed event recovered`
    case 'workflow_audit':
      return `Workflow ran: ${d.title ?? ''}`.trim()
    default:
      return log.action.replace(/_/g, ' ')
  }
}
