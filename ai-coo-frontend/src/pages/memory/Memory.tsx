import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Grid3x3,
  List,
  Pin,
  Plus,
  Search,
  Star,
  Tag as TagIcon,
  X,
} from 'lucide-react'
import { memoryService, type MemoryEntry, type MemoryStatusFilter } from '@/services/memory'
import { useAuthStore } from '@/store/authStore'
import Badge from '@/components/ui/Badge'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/Button'
import { getCategoryIcon, getCategoryLabel, getImportanceTone, ALL_CATEGORIES } from '@/lib/memoryDisplay'
import { formatDistanceToNow } from 'date-fns'
import MemoryFormModal from './MemoryFormModal'
import MemoryDetailDrawer from './MemoryDetailDrawer'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function selectClass() {
  return 'rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]'
}

const PAGE_SIZE = 24
const STATUS_TABS: { value: MemoryStatusFilter; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'archived', label: 'Archived' },
  { value: 'all', label: 'All' },
]

type ViewMode = 'grid' | 'list'

export default function Memory() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()

  const [view, setView] = useState<ViewMode>('grid')
  const [statusTab, setStatusTab] = useState<MemoryStatusFilter>('active')
  const [category, setCategory] = useState<string | null>(null)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [importance, setImportance] = useState('')
  const [pinnedOnly, setPinnedOnly] = useState(false)
  const [favoritedOnly, setFavoritedOnly] = useState(false)
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'last_accessed_at'>('created_at')
  const [offset, setOffset] = useState(0)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<MemoryEntry | null>(null)

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput)
      setOffset(0)
    }, 350)
    return () => clearTimeout(t)
  }, [searchInput])

  useEffect(() => {
    setOffset(0)
  }, [statusTab, category, importance, pinnedOnly, favoritedOnly, sortBy])

  const filters = useMemo(
    () => ({
      status: statusTab,
      ...(category ? { category } : {}),
      ...(importance ? { importance: importance as 'low' | 'medium' | 'high' | 'critical' } : {}),
      ...(pinnedOnly ? { pinned: true } : {}),
      ...(favoritedOnly ? { favorited: true } : {}),
      ...(search ? { search } : {}),
      sort_by: sortBy,
      sort_dir: 'desc' as const,
    }),
    [statusTab, category, importance, pinnedOnly, favoritedOnly, search, sortBy]
  )

  const { data: filterOptions } = useQuery({
    queryKey: ['memory', 'filters', orgId],
    queryFn: () => memoryService.getFilterOptions(orgId!),
    enabled: !!orgId,
  })

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['memory', 'list', orgId, PAGE_SIZE, offset, filters],
    queryFn: () => memoryService.list(orgId!, PAGE_SIZE, offset, filters),
    enabled: !!orgId,
    placeholderData: (prev) => prev,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const page = Math.floor(offset / PAGE_SIZE) + 1
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    if (!isLoading && !isFetching && offset > 0 && items.length === 0 && total > 0) {
      setOffset((o) => Math.max(0, o - PAGE_SIZE))
    }
  }, [isLoading, isFetching, items.length, total, offset])

  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set())

  function withPending<T>(id: string, fn: () => Promise<T>): Promise<T> {
    setPendingIds((prev) => new Set(prev).add(id))
    return fn().finally(() => {
      setPendingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    })
  }

  const listQueryKey = ['memory', 'list', orgId, PAGE_SIZE, offset, filters] as const

  const pinMutation = useMutation({
    mutationFn: (m: MemoryEntry) =>
      withPending(m.id, () => (m.pinned ? memoryService.unpin(m.id, orgId!) : memoryService.pin(m.id, orgId!))),
    onMutate: async (m: MemoryEntry) => {
      await queryClient.cancelQueries({ queryKey: ['memory', 'list'] })
      const prev = queryClient.getQueryData(listQueryKey)
      queryClient.setQueryData(listQueryKey, (old: typeof data) =>
        old
          ? { ...old, items: old.items.map((it) => (it.id === m.id ? { ...it, pinned: !it.pinned } : it)) }
          : old
      )
      return { prev }
    },
    onError: (_err, _m, context) => {
      if (context?.prev) queryClient.setQueryData(listQueryKey, context.prev)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['memory'] }),
  })

  const favoriteMutation = useMutation({
    mutationFn: (m: MemoryEntry) =>
      withPending(m.id, () =>
        m.favorited ? memoryService.unfavorite(m.id, orgId!) : memoryService.favorite(m.id, orgId!)
      ),
    onMutate: async (m: MemoryEntry) => {
      await queryClient.cancelQueries({ queryKey: ['memory', 'list'] })
      const prev = queryClient.getQueryData(listQueryKey)
      queryClient.setQueryData(listQueryKey, (old: typeof data) =>
        old
          ? { ...old, items: old.items.map((it) => (it.id === m.id ? { ...it, favorited: !it.favorited } : it)) }
          : old
      )
      return { prev }
    },
    onError: (_err, _m, context) => {
      if (context?.prev) queryClient.setQueryData(listQueryKey, context.prev)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['memory'] }),
  })

  function openDetail(id: string) {
    setSelectedId(id)
    memoryService.access(id, orgId!).then(() => {
      queryClient.invalidateQueries({ queryKey: ['memory', 'list'] })
    })
  }

  function openCreate() {
    setEditing(null)
    setFormOpen(true)
  }

  function openEdit(m: MemoryEntry) {
    setEditing(m)
    setFormOpen(true)
  }

  const hasActiveFilters = !!(category || importance || pinnedOnly || favoritedOnly)

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Memory
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            What AI COO remembers about your users, projects, and preferences
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus size={14} />
          New memory
        </Button>
      </div>

      <div className="flex flex-col lg:flex-row gap-5">
        <aside className="lg:w-56 shrink-0">
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-3 lg:sticky lg:top-6">
            <button
              onClick={() => setCategory(null)}
              className={
                category === null
                  ? 'w-full text-left flex items-center gap-2 rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]'
                  : 'w-full text-left flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] transition-colors'
              }
            >
              <TagIcon size={14} />
              All categories
            </button>
            {(filterOptions?.categories ?? ALL_CATEGORIES).map((c) => {
              const Icon = getCategoryIcon(c)
              return (
                <button
                  key={c}
                  onClick={() => setCategory(c)}
                  className={
                    category === c
                      ? 'w-full text-left flex items-center gap-2 rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]'
                      : 'w-full text-left flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] transition-colors'
                  }
                >
                  <Icon size={14} />
                  {getCategoryLabel(c)}
                </button>
              )
            })}
          </div>
        </aside>

        <div className="flex-1 min-w-0">
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-5">
            <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-1 w-fit mb-4">
              {STATUS_TABS.map((tab) => (
                <button
                  key={tab.value}
                  onClick={() => setStatusTab(tab.value)}
                  className={
                    statusTab === tab.value
                      ? 'rounded-md bg-[var(--color-surface-hover)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)]'
                      : 'rounded-md px-3 py-1.5 text-xs font-medium text-[var(--color-text-faint)] hover:text-[var(--color-text-muted)]'
                  }
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3 flex-wrap mb-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)]" />
                <input
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search title or content..."
                  aria-label="Search memories"
                  className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] pl-9 pr-3 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]"
                />
              </div>

              <select value={importance} onChange={(e) => setImportance(e.target.value)} className={selectClass()}>
                <option value="">All importance</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>

              <select value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)} className={selectClass()}>
                <option value="created_at">Newest</option>
                <option value="updated_at">Recently updated</option>
                <option value="last_accessed_at">Recently accessed</option>
              </select>

              <button
                onClick={() => setPinnedOnly((v) => !v)}
                className={
                  pinnedOnly
                    ? 'flex items-center gap-1.5 rounded-lg border border-[var(--color-signal)] text-[var(--color-signal)] px-3 py-2 text-xs'
                    : 'flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text-muted)] px-3 py-2 text-xs hover:border-[var(--color-border-hover)]'
                }
              >
                <Pin size={13} />
                Pinned
              </button>

              <button
                onClick={() => setFavoritedOnly((v) => !v)}
                className={
                  favoritedOnly
                    ? 'flex items-center gap-1.5 rounded-lg border border-[var(--color-signal)] text-[var(--color-signal)] px-3 py-2 text-xs'
                    : 'flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text-muted)] px-3 py-2 text-xs hover:border-[var(--color-border-hover)]'
                }
              >
                <Star size={13} />
                Favorites
              </button>

              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setCategory(null)
                    setImportance('')
                    setPinnedOnly(false)
                    setFavoritedOnly(false)
                  }}
                >
                  <X size={13} />
                  Clear
                </Button>
              )}

              <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-1 ml-auto">
                <button
                  aria-label="Grid view"
                  onClick={() => setView('grid')}
                  className={
                    view === 'grid'
                      ? 'rounded-md bg-[var(--color-surface-hover)] p-1.5 text-[var(--color-text-primary)]'
                      : 'rounded-md p-1.5 text-[var(--color-text-faint)] hover:text-[var(--color-text-muted)]'
                  }
                >
                  <Grid3x3 size={14} />
                </button>
                <button
                  aria-label="List view"
                  onClick={() => setView('list')}
                  className={
                    view === 'list'
                      ? 'rounded-md bg-[var(--color-surface-hover)] p-1.5 text-[var(--color-text-primary)]'
                      : 'rounded-md p-1.5 text-[var(--color-text-faint)] hover:text-[var(--color-text-muted)]'
                  }
                >
                  <List size={14} />
                </button>
              </div>
            </div>

            {isLoading ? (
              <div className={view === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3' : 'space-y-2'}>
                {[...Array(6)].map((_, i) => (
                  <Skeleton key={i} className={view === 'grid' ? 'h-36 w-full' : 'h-14 w-full'} />
                ))}
              </div>
            ) : isError ? (
              <ErrorBanner message="Couldn't load memories. Please try again." />
            ) : items.length === 0 ? (
              <EmptyState
                icon={TagIcon}
                title={search || hasActiveFilters ? 'No matching memories' : statusTab === 'archived' ? 'No archived memories' : 'No memories yet'}
                description={
                  search || hasActiveFilters
                    ? 'Try adjusting your filters or search.'
                    : statusTab === 'archived'
                    ? 'Memories you archive will show up here.'
                    : 'Create your first memory so AI COO can start remembering context.'
                }
                action={
                  !search && !hasActiveFilters && statusTab === 'active' ? (
                    <Button onClick={openCreate}>
                      <Plus size={14} />
                      New memory
                    </Button>
                  ) : undefined
                }
              />
            ) : view === 'grid' ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                {items.map((m) => {
                  const Icon = getCategoryIcon(m.category)
                  return (
                    <div
                      key={m.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => openDetail(m.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          openDetail(m.id)
                        }
                      }}
                      className="cursor-pointer rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 hover:border-[var(--color-border-hover)] transition-colors flex flex-col gap-2 focus:outline-none focus:ring-1 focus:ring-[var(--color-signal)]"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-faint)]">
                          <Icon size={12} />
                          {getCategoryLabel(m.category)}
                        </span>
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            aria-label={m.pinned ? 'Unpin memory' : 'Pin memory'}
                            disabled={pendingIds.has(m.id)}
                            onClick={(e) => {
                              e.stopPropagation()
                              pinMutation.mutate(m)
                            }}
                            className={(m.pinned ? 'text-[var(--color-signal)]' : 'text-[var(--color-text-faint)] hover:text-[var(--color-text-muted)]') + ' disabled:opacity-50'}
                          >
                            <Pin size={13} fill={m.pinned ? 'currentColor' : 'none'} />
                          </button>
                          <button
                            aria-label={m.favorited ? 'Unfavorite memory' : 'Favorite memory'}
                            disabled={pendingIds.has(m.id)}
                            onClick={(e) => {
                              e.stopPropagation()
                              favoriteMutation.mutate(m)
                            }}
                            className={(m.favorited ? 'text-[var(--color-amber)]' : 'text-[var(--color-text-faint)] hover:text-[var(--color-text-muted)]') + ' disabled:opacity-50'}
                          >
                            <Star size={13} fill={m.favorited ? 'currentColor' : 'none'} />
                          </button>
                        </div>
                      </div>

                      <h3 className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                        {m.title ?? 'Untitled'}
                      </h3>
                      <p className="text-xs text-[var(--color-text-muted)] line-clamp-3">{m.content}</p>

                      <div className="mt-auto flex items-center justify-between gap-2 pt-2">
                        <div className="flex items-center gap-1 flex-wrap">
                          {(m.tags ?? []).slice(0, 2).map((t) => (
                            <span key={t} className="text-[10px] text-[var(--color-text-faint)] bg-[var(--color-surface-hover)] rounded px-1.5 py-0.5">
                              {t}
                            </span>
                          ))}
                        </div>
                        <Badge tone={getImportanceTone(m.importance)}>{m.importance ?? 'medium'}</Badge>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex flex-col divide-y divide-[var(--color-border)]">
                {items.map((m) => {
                  const Icon = getCategoryIcon(m.category)
                  return (
                    <div
                      key={m.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => openDetail(m.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          openDetail(m.id)
                        }
                      }}
                      className="cursor-pointer py-3 flex items-center gap-3 hover:bg-[var(--color-surface-hover)] transition-colors px-2 -mx-2 rounded-lg focus:outline-none focus:ring-1 focus:ring-[var(--color-signal)]"
                    >
                      <Icon size={14} className="text-[var(--color-text-faint)] shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-[var(--color-text-primary)] truncate">{m.title ?? 'Untitled'}</p>
                        <p className="text-xs text-[var(--color-text-faint)] truncate">{m.content}</p>
                      </div>
                      {m.pinned && <Pin size={12} className="text-[var(--color-signal)] shrink-0" fill="currentColor" />}
                      {m.favorited && <Star size={12} className="text-[var(--color-amber)] shrink-0" fill="currentColor" />}
                      <Badge tone={getImportanceTone(m.importance)} className="shrink-0">{m.importance ?? 'medium'}</Badge>
                      <span className="text-xs text-[var(--color-text-faint)] font-mono shrink-0 w-24 text-right">
                        {formatDistanceToNow(new Date(m.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}

            {items.length > 0 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-[var(--color-border)]">
                <span className="text-xs text-[var(--color-text-faint)]">
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
          </div>
        </div>
      </div>

      <MemoryFormModal
        open={formOpen}
        orgId={orgId!}
        memory={editing}
        onClose={() => setFormOpen(false)}
        onSuccess={() => setFormOpen(false)}
      />

      <MemoryDetailDrawer
        open={!!selectedId}
        memoryId={selectedId}
        orgId={orgId!}
        onClose={() => setSelectedId(null)}
        onEdit={(m) => {
          setSelectedId(null)
          openEdit(m)
        }}
      />
    </div>
  )
}
