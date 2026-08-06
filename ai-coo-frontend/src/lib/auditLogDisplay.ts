import {
  ListTodo,
  Workflow,
  GitCommitHorizontal,
  ShieldCheck,
  GitBranch,
  Mail,
  Calendar,
  Plug,
  Settings,
  User,
  ScrollText,
  type LucideIcon,
} from 'lucide-react'
import type { AuditStatus } from '@/services/audit-logs'

// Maps a module string (free text on the backend, so new modules "just work"
// with a sensible fallback icon) to its display icon.
export const MODULE_ICON: Record<string, LucideIcon> = {
  tasks: ListTodo,
  workflows: Workflow,
  commit_scheduler: GitCommitHorizontal,
  human_approval: ShieldCheck,
  github: GitBranch,
  gmail: Mail,
  calendar: Calendar,
  integrations: Plug,
  settings: Settings,
  auth: User,
  system: ScrollText,
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
  calendar: 'Calendar',
  integrations: 'Integrations',
  settings: 'Settings',
  auth: 'Authentication',
  system: 'System',
}

export function getModuleLabel(module: string | null): string {
  if (!module) return 'System'
  return MODULE_LABELS[module] ?? module.replace(/_/g, ' ')
}

type BadgeTone = 'signal' | 'alert' | 'amber' | 'neutral'

// success -> signal (green), failed -> alert (red), warning -> amber, info -> neutral.
// Matches the existing tone vocabulary used across Badge in the rest of the app.
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
