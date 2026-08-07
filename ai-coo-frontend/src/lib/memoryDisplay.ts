import {
  User,
  FolderKanban,
  GitBranch,
  Workflow,
  MessageSquare,
  Plug,
  BookOpen,
  Tag,
  type LucideIcon,
} from 'lucide-react'

// Free-text category on the backend (same philosophy as audit_logs' module
// field) so new categories work with a sensible fallback icon/label without
// a schema change.
export const CATEGORY_ICON: Record<string, LucideIcon> = {
  user_preference: User,
  project: FolderKanban,
  repository: GitBranch,
  workflow: Workflow,
  conversation: MessageSquare,
  integration: Plug,
  knowledge: BookOpen,
  custom: Tag,
}

export function getCategoryIcon(category: string | null): LucideIcon {
  if (!category) return Tag
  return CATEGORY_ICON[category] ?? Tag
}

export const CATEGORY_LABELS: Record<string, string> = {
  user_preference: 'User Preference',
  project: 'Project',
  repository: 'Repository',
  workflow: 'Workflow',
  conversation: 'Conversation',
  integration: 'Integration',
  knowledge: 'Knowledge',
  custom: 'Custom',
}

export function getCategoryLabel(category: string | null): string {
  if (!category) return 'Uncategorized'
  return CATEGORY_LABELS[category] ?? category.replace(/_/g, ' ')
}

export const ALL_CATEGORIES = Object.keys(CATEGORY_LABELS)

type BadgeTone = 'signal' | 'alert' | 'amber' | 'neutral'

export function getImportanceTone(importance: string | null): BadgeTone {
  switch (importance) {
    case 'critical':
      return 'alert'
    case 'high':
      return 'amber'
    case 'medium':
      return 'signal'
    default:
      return 'neutral'
  }
}
