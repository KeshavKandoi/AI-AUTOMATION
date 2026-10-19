



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
