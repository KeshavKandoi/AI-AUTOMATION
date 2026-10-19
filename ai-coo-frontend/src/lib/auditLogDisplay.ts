import {
  ListTodo,
  Workflow,
  GitCommitHorizontal,
  ShieldCheck,
  GitBranch,
  Mail,
  Plug,
  Settings,
  User,
  ScrollText,
  Brain,
  Briefcase,
  type LucideIcon,
} from 'lucide-react'
import type { AuditStatus } from '@/services/audit-logs'



export const MODULE_ICON: Record<string, LucideIcon> = {
  tasks: ListTodo,
  workflows: Workflow,
  commit_scheduler: GitCommitHorizontal,
  human_approval: ShieldCheck,
  github: GitBranch,
  gmail: Mail,
  integrations: Plug,
  settings: Settings,
  auth: User,
  system: ScrollText,
  memory: Brain,
  job_hunter: Briefcase,
}

export function getModuleIcon(module: string | null): LucideIcon {
  if (!module) return ScrollText
  return MODULE_ICON[module] ?? ScrollText
}

export const MODULE_LABELS: Record<string, string> = {
  tasks: 'Tasks',
  workflows: 'Workflows',
  commit_scheduler: 'Commit Scheduler',
  human_approval: 'Human Approval',
  github: 'GitHub',
  gmail: 'Gmail',
  integrations: 'Integrations',
  settings: 'Settings',
  auth: 'Authentication',
  system: 'System',
  memory: 'Memory',
  job_hunter: 'Job Hunter',
}

export function getModuleLabel(module: string | null): string {
  if (!module) return 'System'
  return MODULE_LABELS[module] ?? module.replace(/_/g, ' ')
}

type BadgeTone = 'signal' | 'alert' | 'amber' | 'neutral'



export function getStatusTone(status: AuditStatus | string | null): BadgeTone {
  switch (status) {
    case 'success':
      return 'signal'
    case 'failed':
      return 'alert'
    case 'warning':
      return 'amber'
    default:
      return 'neutral'
  }
}

export function formatActionLabel(action: string): string {
  return action.replace(/_/g, ' ')
}
