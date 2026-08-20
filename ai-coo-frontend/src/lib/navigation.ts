import {
  LayoutDashboard, MessageSquare, ListTodo, Workflow, GitBranch, Mail,
  Calendar, GitCommitHorizontal, GitPullRequest, ShieldCheck, ScrollText,
  Plug, Brain, Bell, BarChart3, Settings, Briefcase, GitFork,
} from 'lucide-react'

export interface NavItem {
  label: string
  path: string
  icon: typeof LayoutDashboard
  comingSoon?: boolean
}

export const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'AI COO Chat', path: '/chat', icon: MessageSquare, comingSoon: true },
  { label: 'Tasks', path: '/tasks', icon: ListTodo },
  { label: 'Workflow Automations', path: '/workflows', icon: Workflow },
  { label: 'GitHub', path: '/integrations/github', icon: GitBranch },
  { label: 'Gmail', path: '/integrations/gmail', icon: Mail },
  { label: 'Google Calendar', path: '/integrations/calendar', icon: Calendar },
  { label: 'Commit Scheduler', path: '/commit-scheduler', icon: GitCommitHorizontal },
  { label: 'Open Source', path: '/open-source', icon: GitFork },
  { label: 'Pull Requests', path: '/pull-requests', icon: GitPullRequest },
  { label: 'Human Approval', path: '/approvals', icon: ShieldCheck },
  { label: 'Job Hunter', path: '/job-hunter', icon: Briefcase },
  { label: 'Audit Logs', path: '/audit-logs', icon: ScrollText },
  { label: 'Integrations', path: '/integrations', icon: Plug },
  { label: 'Memory', path: '/memory', icon: Brain },
  { label: 'Notifications', path: '/notifications', icon: Bell },
  { label: 'Analytics', path: '/analytics', icon: BarChart3, comingSoon: true },
  { label: 'Settings', path: '/settings', icon: Settings },
]
