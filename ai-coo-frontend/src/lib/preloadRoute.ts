const routeChunks: Record<string, () => Promise<unknown>> = {
  '/dashboard': () => import('@/pages/dashboard/Dashboard'),
  '/tasks': () => import('@/pages/tasks/Tasks'),
  '/integrations/github': () => import('@/pages/github/GitHub'),
  '/approvals': () => import('@/pages/approvals/HumanApproval'),
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

let backgroundPreloadStarted = false

export function preloadNavigationRoutes() {
  if (backgroundPreloadStarted) return
  backgroundPreloadStarted = true

  const load = async () => {
    // Fetch page code after the current screen has had time to render. Keep
    // the largest page last so it cannot delay normal navigation or API work.
    const paths = Object.keys(routeChunks).filter((path) => path !== '/analytics')
    paths.push('/analytics')
    for (const path of paths) {
      if (document.visibilityState !== 'visible') break
      try {
        await routeChunks[path]()
      } catch {
        // The normal route boundary and Vite's chunk recovery handle errors.
      }
      await new Promise((resolve) => window.setTimeout(resolve, 100))
    }
  }

  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(() => void load(), { timeout: 4_000 })
  } else {
    setTimeout(() => void load(), 500)
  }
}
