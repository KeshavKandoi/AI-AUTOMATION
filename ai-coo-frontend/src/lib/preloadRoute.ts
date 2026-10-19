const routeChunks: Record<string, () => Promise<unknown>> = {
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
