import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  ListFilter,
  ScrollText,
  Search,
  SortAsc,
  SortDesc,
  X,
} from 'lucide-react'
import { auditLogsService, type AuditLogEntry, type AuditStatus } from '@/services/audit-logs'
import { useAuthStore } from '@/store/authStore'
import Badge from '@/components/ui/Badge'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from '@/components/ui/Table'
import { formatDistanceToNow } from 'date-fns'
import { getModuleIcon, getModuleLabel, getStatusTone, formatActionLabel } from '@/lib/auditLogDisplay'
import AuditLogDetailDrawer from './AuditLogDetailDrawer'
import AuditLogTimeline from './AuditLogTimeline'

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

function selectClass() {
  return 'rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]'
}

const STATUS_OPTIONS: AuditStatus[] = ['success', 'failed', 'warning', 'info']
const PAGE_SIZE = 25

type ViewMode = 'table' | 'timeline'

export default function AuditLogs() {
  const orgId = useAuthStore((s) => s.user?.organization_id)

  const [view, setView] = useState<ViewMode>('table')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [module, setModule] = useState('')
  const [status, setStatus] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [offset, setOffset] = useState(0)
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(false)

  // Debounce free-text search so we don't fire a request per keystroke.
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput)
      setOffset(0)
    }, 350)
    return () => clearTimeout(t)
  }, [searchInput])

  useEffect(() => {
    setOffset(0)
  }, [module, status, startDate, endDate, sortDir])

  const filters = useMemo(
    () => ({
      ...(module ? { module } : {}),
      ...(status ? { status: status as AuditStatus } : {}),
      ...(startDate ? { start_date: new Date(startDate).toISOString() } : {}),
      ...(endDate ? { end_date: new Date(endDate + 'T23:59:59').toISOString() } : {}),
      ...(search ? { search } : {}),
      sort_dir: sortDir,
    }),
    [module, status, startDate, endDate, search, sortDir]
  )

  const { data: filterOptions } = useQuery({
    queryKey: ['audit-logs', 'filters', orgId],
    queryFn: () => auditLogsService.getFilterOptions(orgId!),
    enabled: !!orgId,
  })

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['audit-logs', 'list', orgId, PAGE_SIZE, offset, filters],
    queryFn: () => auditLogsService.list(orgId!, PAGE_SIZE, offset, filters),
    enabled: !!orgId,
    placeholderData: (prev) => prev,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const page = Math.floor(offset / PAGE_SIZE) + 1
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const hasActiveFilters = !!(module || status || startDate || endDate)

  function clearFilters() {
    setModule('')
    setStatus('')
    setStartDate('')
    setEndDate('')
  }

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Audit Logs
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            A complete timeline of every action across Workforge
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-1">
          <button
            onClick={() => setView('table')}
            className={
              view === 'table'
                ? 'flex items-center gap-1.5 rounded-md bg-[var(--color-surface-hover)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)]'
                : 'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-[var(--color-text-faint)] hover:text-[var(--color-text-muted)]'
            }
          >
            <ListFilter size={13} />
            Table
          </button>
          <button
            onClick={() => setView('timeline')}
            className={
              view === 'timeline'
                ? 'flex items-center gap-1.5 rounded-md bg-[var(--color-surface-hover)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)]'
                : 'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-[var(--color-text-faint)] hover:text-[var(--color-text-muted)]'
            }
          >
            <ScrollText size={13} />
            Timeline
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl p-5">
        <div className="flex items-center gap-3 flex-wrap mb-4">
          <div className="relative flex-1 min-w-[220px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)]" />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search summary or action..."
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] pl-9 pr-3 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]"
            />
          </div>

          <Button
            variant="secondary"
            onClick={() => setFiltersOpen((v) => !v)}
            className={hasActiveFilters ? 'border-[var(--color-signal)] text-[var(--color-signal)]' : ''}
          >
            <ListFilter size={14} />
            Filters
            {hasActiveFilters && <Badge tone="signal">On</Badge>}
          </Button>

          <button
            type="button"
            onClick={() => setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))}
            title={sortDir === 'desc' ? 'Newest first' : 'Oldest first'}
            className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-xs text-[var(--color-text-muted)] hover:border-[var(--color-border-hover)] transition-colors"
          >
            {sortDir === 'desc' ? <SortDesc size={14} /> : <SortAsc size={14} />}
            {sortDir === 'desc' ? 'Newest' : 'Oldest'}
          </button>
        </div>

        {filtersOpen && (
          <div className="flex items-end gap-3 flex-wrap mb-4 pb-4 border-b border-[var(--color-border)]">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-[var(--color-text-faint)]">Module</label>
              <select value={module} onChange={(e) => setModule(e.target.value)} className={selectClass()}>
                <option value="">All modules</option>
                {filterOptions?.modules.map((m) => (
                  <option key={m} value={m}>
                    {getModuleLabel(m)}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-[var(--color-text-faint)]">Status</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)} className={selectClass()}>
                <option value="">All statuses</option>
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <Input label="From" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            <Input label="To" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            {hasActiveFilters && (
              <Button variant="ghost" onClick={clearFilters}>
                <X size={13} />
                Clear
              </Button>
            )}
          </div>
        )}

        {isLoading ? (
          <div className="space-y-2">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-11 w-full" />
            ))}
          </div>
        ) : isError ? (
          <ErrorBanner message="Couldn't load audit logs. Please try again." />
        ) : items.length === 0 ? (
          <EmptyState
            icon={ScrollText}
            title={hasActiveFilters || search ? 'No matching audit logs' : 'No activity yet'}
            description={
              hasActiveFilters || search
                ? 'Try adjusting your filters or search.'
                : 'Actions across Workforge will show up here as they happen.'
            }
          />
        ) : view === 'table' ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Module</TableHeaderCell>
                <TableHeaderCell>Action</TableHeaderCell>
                <TableHeaderCell>Summary</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell className="text-right">When</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((log: AuditLogEntry) => {
                const Icon = getModuleIcon(log.module)
                return (
                  <TableRow
                    key={log.id}
                    className="cursor-pointer"
                    onClick={() => setSelectedLogId(log.id)}
                  >
                    <TableCell>
                      <span className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                        <Icon size={13} />
                        {getModuleLabel(log.module)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs">{formatActionLabel(log.action)}</span>
                    </TableCell>
                    <TableCell className="max-w-[320px]">
                      <span className="truncate block text-sm">
                        {log.summary ?? formatActionLabel(log.action)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge tone={getStatusTone(log.status)}>{log.status ?? 'info'}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="text-xs text-[var(--color-text-faint)] font-mono">
                        {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                      </span>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        ) : (
          <AuditLogTimeline logs={items} onSelect={setSelectedLogId} />
        )}

        {items.length > 0 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-[var(--color-border)]">
            <span className="text-xs text-[var(--color-text-faint)]">
              {total} total · page {page} of {totalPages}
              {isFetching && ' · updating...'}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
              >
                <ChevronLeft size={14} />
                Prev
              </Button>
              <Button
                variant="secondary"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
              >
                Next
                <ChevronRight size={14} />
              </Button>
            </div>
          </div>
        )}
      </div>

      <AuditLogDetailDrawer
        open={!!selectedLogId}
        logId={selectedLogId}
        onClose={() => setSelectedLogId(null)}
      />
    </div>
  )
}
