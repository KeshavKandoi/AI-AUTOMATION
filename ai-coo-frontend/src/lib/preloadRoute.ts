const routeChunks: Record<string, () => Promise<unknown>> = {
  '/dashboard': () => import('@/pages/dashboard/Dashboard'),
  '/tasks': () => import('@/pages/tasks/Tasks'),
  '/integrations/github': () => import('@/pages/github/GitHub'),
  '/audit-logs': () => import('@/pages/auditLogs/AuditLogs'),
  '/notifications': () => import('@/pages/notifications/Notifications'),
  '/settings': () => import('@/pages/settings/Settings'),
  '/open-source': () => import('@/pages/openSource/OpenSource'),
  '/pull-requests': () => import('@/pages/pullRequests/PullRequests'),
  '/job-hunter': () => import('@/pages/jobHunter/JobHunter'),
  '/analytics': () => import('@/pages/analytics/Analytics'),
  '/integrations': () => import('@/pages/integrations/Integrations'),
  '/workflows': () => import('@/pages/workflows/Workflows'),
  '/commit-scheduler': () => import('@/pages/commitScheduler/CommitScheduler'),
}

export function preloadRoute(path: string) {
  void routeChunks[path]?.().catch(() => undefined)
}
