import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Bell, CheckCheck } from 'lucide-react'
import { notificationsService, type NotificationEntry } from '@/services/notifications'
import { useAuthStore } from '@/store/authStore'
import Badge from '@/components/ui/Badge'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/Button'
import { getModuleIcon, getModuleLabel } from '@/lib/auditLogDisplay'
import { getPriorityTone } from '@/lib/notificationDisplay'
import { formatDistanceToNow } from 'date-fns'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-alert-dim bg-alert-dim px-3 py-2 text-xs text-alert">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function selectClass() {
  return 'rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-signal focus:ring-1 focus:ring-signal'
}

const PAGE_SIZE = 25
const KNOWN_MODULES = ['tasks', 'workflows', 'commit_scheduler', 'github', 'gmail', 'integrations', 'memory', 'job_hunter']

export default function Notifications() {
  const reducedMotion = useReducedMotion()
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const [unreadOnly, setUnreadOnly] = useState(false)
  const [module, setModule] = useState('')
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    setOffset(0)
  }, [unreadOnly, module])

  const filters = useMemo(
    () => ({
      ...(unreadOnly ? { unread_only: true } : {}),
      ...(module ? { module } : {}),
    }),
    [unreadOnly, module]
  )

  const listQueryKey = ['notifications', 'list', orgId, PAGE_SIZE, offset, filters] as const

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: listQueryKey,
    queryFn: () => notificationsService.list(orgId!, PAGE_SIZE, offset, filters),
    enabled: !!orgId,
    placeholderData: (prev) => prev,
    refetchInterval: 30000,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const unreadCount = data?.unread_count ?? 0
  const page = Math.floor(offset / PAGE_SIZE) + 1
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const markReadMutation = useMutation({
    mutationFn: (n: NotificationEntry) => notificationsService.markRead(n.id, orgId!),
    onMutate: async (n: NotificationEntry) => {
      await queryClient.cancelQueries({ queryKey: ['notifications', 'list'] })
      const prev = queryClient.getQueryData(listQueryKey)
      queryClient.setQueryData(listQueryKey, (old: typeof data) =>
        old
          ? {
              ...old,
              items: old.items.map((it) => (it.id === n.id ? { ...it, read: true } : it)),
              unread_count: Math.max(0, old.unread_count - (n.read ? 0 : 1)),
            }
          : old
      )
      return { prev }
    },
    onError: (_err, _n, context) => {
      if (context?.prev) queryClient.setQueryData(listQueryKey, context.prev)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsService.markAllRead(orgId!),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['notifications', 'list'] })
      const prev = queryClient.getQueryData(listQueryKey)
      queryClient.setQueryData(listQueryKey, (old: typeof data) =>
        old ? { ...old, items: old.items.map((it) => ({ ...it, read: true })), unread_count: 0 } : old
      )
      return { prev }
    },
    onError: (_err, _vars, context) => {
      if (context?.prev) queryClient.setQueryData(listQueryKey, context.prev)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  function handleClick(n: NotificationEntry) {
    if (!n.read) markReadMutation.mutate(n)
    if (n.action_url) navigate(n.action_url)
  }

  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto">
      <motion.div initial={reducedMotion ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }} className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-2xl font-semibold text-text-primary">
            Notifications
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Everything WorkForge wants you to know, in one place
          </p>
        </div>
        <Button
          variant="secondary"
          disabled={unreadCount === 0}
          loading={markAllReadMutation.isPending}
          onClick={() => markAllReadMutation.mutate()}
        >
          <CheckCheck size={14} />
          Mark all read
        </Button>
      </motion.div>

      <motion.div initial={reducedMotion ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.06 }} className="rounded-2xl border border-border bg-surface/60 backdrop-blur-xl p-5">
        <div className="flex items-center gap-3 flex-wrap mb-4">
          <button
            onClick={() => setUnreadOnly((v) => !v)}
            className={
              unreadOnly
                ? 'flex items-center gap-1.5 rounded-lg border border-signal text-signal px-3 py-2 text-xs'
                : 'flex items-center gap-1.5 rounded-lg border border-border text-text-muted px-3 py-2 text-xs hover:border-border-hover'
            }
          >
            Unread only
            {unreadCount > 0 && <Badge tone="signal">{unreadCount}</Badge>}
          </button>

          <select value={module} onChange={(e) => setModule(e.target.value)} className={selectClass()}>
            <option value="">All modules</option>
            {KNOWN_MODULES.map((m) => (
              <option key={m} value={m}>
                {getModuleLabel(m)}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : isError ? (
          <ErrorBanner message="Couldn't load notifications. Please try again." />
        ) : items.length === 0 ? (
          <EmptyState
            icon={Bell}
            title={unreadOnly || module ? 'No matching notifications' : 'No notifications yet'}
            description={
              unreadOnly || module
                ? 'Try adjusting your filters.'
                : "You're all caught up — new activity across WorkForge will show up here."
            }
          />
        ) : (
          <div className="flex flex-col divide-y divide-border">
            <AnimatePresence initial={false}>
            {items.map((n, index) => {
              const Icon = getModuleIcon(n.module)
              return (
                <motion.button
                  key={n.id}
                  layout={!reducedMotion}
                  initial={reducedMotion ? false : { opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={reducedMotion ? undefined : { opacity: 0, x: 8 }}
                  transition={{ duration: 0.22, delay: Math.min(index, 6) * 0.035 }}
                  onClick={() => handleClick(n)}
                  className="w-full text-left py-3 flex items-start gap-3 hover:bg-surface-hover transition-colors px-2 -mx-2 rounded-lg focus:outline-none focus:ring-1 focus:ring-signal"
                >
                  <span className="relative flex items-center justify-center h-8 w-8 rounded-lg bg-surface-hover shrink-0 mt-0.5">
                    <Icon size={14} className="text-text-muted" />
                    {!n.read && (
                      <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-signal" />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className={n.read ? 'text-sm text-text-muted' : 'text-sm text-text-primary font-medium'}>
                        {n.title}
                      </p>
                      {n.priority !== 'normal' && <Badge tone={getPriorityTone(n.priority)}>{n.priority}</Badge>}
                    </div>
                    <p className="mt-0.5 text-xs text-text-faint line-clamp-2">{n.body}</p>
                    <div className="mt-1 flex items-center gap-2 text-[11px] text-text-faint">
                      <span>{getModuleLabel(n.module)}</span>
                      <span>·</span>
                      <span>{formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}</span>
                      {n.action_label && (
                        <>
                          <span>·</span>
                          <span className="text-signal">{n.action_label}</span>
                        </>
                      )}
                    </div>
                  </div>
                </motion.button>
              )
            })}
            </AnimatePresence>
          </div>
        )}

        {items.length > 0 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
            <span className="text-xs text-text-faint">
              {total} total · page {page} of {totalPages}
              {isFetching && ' · updating...'}
            </span>
            <div className="flex items-center gap-2">
              <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}>
                Prev
              </Button>
              <Button variant="secondary" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset((o) => o + PAGE_SIZE)}>
                Next
              </Button>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}
