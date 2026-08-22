import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3, AlertCircle, ListTodo, Workflow, GitCommitHorizontal, RefreshCw,
} from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'
import { useAuthStore } from '@/store/authStore'
import { analyticsService, type AnalyticsRangePreset } from '@/services/analytics'
import StatCard from '@/components/ui/StatCard'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import EmptyState from '@/components/ui/EmptyState'
import {
  Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell,
} from '@/components/ui/Table'

const RANGE_OPTIONS: { label: string; value: AnalyticsRangePreset; days: number }[] = [
  { label: '7 days', value: '7d', days: 7 },
  { label: '30 days', value: '30d', days: 30 },
  { label: '90 days', value: '90d', days: 90 },
]

function toISODate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function formatShortDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00Z')
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

const STATUS_TONE: Record<string, 'signal' | 'alert' | 'amber' | 'neutral'> = {
  success: 'signal',
  failed: 'alert',
  warning: 'amber',
  skipped: 'amber',
  partial_failure: 'alert',
  skipped_conditions: 'amber',
}

function BreakdownTable({
  title,
  items,
  emptyLabel,
}: {
  title: string
  items: { label: string; count: number }[]
  emptyLabel: string
}) {
  return (
    <Card className="p-5">
      <h2 className="text-sm font-medium text-[var(--color-text-primary)] mb-4">{title}</h2>
      {items.length > 0 ? (
        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell>Status</TableHeaderCell>
              <TableHeaderCell className="text-right">Count</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.label}>
                <TableCell>
                  <Badge tone={STATUS_TONE[item.label] ?? 'neutral'}>{item.label}</Badge>
                </TableCell>
                <TableCell className="text-right font-mono">{item.count}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <p className="text-sm text-[var(--color-text-faint)] py-6 text-center">{emptyLabel}</p>
      )}
    </Card>
  )
}

export default function Analytics() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const [range, setRange] = useState<AnalyticsRangePreset>('30d')

  const { startDate, endDate } = useMemo(() => {
    const days = RANGE_OPTIONS.find((r) => r.value === range)?.days ?? 30
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - (days - 1))
    return { startDate: toISODate(start), endDate: toISODate(end) }
  }, [range])

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['analytics-summary', orgId, startDate, endDate],
    queryFn: () => analyticsService.getSummary(orgId!, startDate, endDate),
    enabled: !!orgId,
  })

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
            Analytics
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Operational overview of AI COO activity and performance
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-xl border border-[var(--color-border)] p-1 bg-[var(--color-surface)]/60">
            {RANGE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setRange(opt.value)}
                className={
                  opt.value === range
                    ? 'px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-surface-hover)] text-[var(--color-text-primary)]'
                    : 'px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
                }
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="h-8 w-8 flex items-center justify-center rounded-lg border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
            aria-label="Refresh"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {isError ? (
        <Card className="p-8">
          <EmptyState
            icon={AlertCircle}
            title="Couldn't load analytics"
            description={error instanceof Error ? error.message : 'Something went wrong fetching analytics data.'}
            action={
              <button
                onClick={() => refetch()}
                className="mt-2 text-xs px-3 py-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]"
              >
                Try again
              </button>
            }
          />
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard
              label="Total events"
              value={data?.total_events ?? 0}
              icon={BarChart3}
              tone="signal"
              loading={isLoading}
            />
            <StatCard
              label="Failed events"
              value={data?.failed_events ?? 0}
              icon={AlertCircle}
              tone="alert"
              loading={isLoading}
            />
            <StatCard
              label="Open tasks"
              value={data?.tasks.open ?? 0}
              icon={ListTodo}
              tone="amber"
              loading={isLoading}
            />
            <StatCard
              label="Workflow runs"
              value={data?.workflows.total_runs ?? 0}
              icon={Workflow}
              tone="signal"
              loading={isLoading}
            />
          </div>

          <Card className="p-5 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-[var(--color-text-primary)]">Activity trend</h2>
              {data && !data.activity_data_complete && (
                <span className="text-[10px] uppercase tracking-wide text-[var(--color-amber)] bg-[var(--color-amber-dim)] rounded px-2 py-1">
                  Partial data — narrow the date range for full detail
                </span>
              )}
            </div>
            {isLoading ? (
              <div className="h-64 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
            ) : data && data.total_events > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={data.activity_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={formatShortDate}
                    tick={{ fontSize: 11, fill: 'var(--color-text-faint)' }}
                  />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-faint)' }} allowDecimals={false} />
                  <Tooltip
                    labelFormatter={(v) => formatShortDate(String(v))}
                    contentStyle={{
                      background: 'var(--color-surface)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="success" stackId="a" fill="var(--color-signal)" name="Success" />
                  <Bar dataKey="warning" stackId="a" fill="var(--color-amber)" name="Warning" />
                  <Bar dataKey="failed" stackId="a" fill="var(--color-alert)" name="Failed" />
                  <Bar dataKey="info" stackId="a" fill="var(--color-text-faint)" name="Info" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                icon={BarChart3}
                title="No activity in this range"
                description="Nothing was logged in the selected time period."
              />
            )}
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <Card className="p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-medium text-[var(--color-text-primary)]">Activity by module</h2>
                {data && !data.activity_data_complete && (
                  <span className="text-[10px] uppercase tracking-wide text-[var(--color-amber)] bg-[var(--color-amber-dim)] rounded px-2 py-1">
                    Partial
                  </span>
                )}
              </div>
              {isLoading ? (
                <div className="space-y-2">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-9 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
                  ))}
                </div>
              ) : data && data.module_breakdown.length > 0 ? (
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableHeaderCell>Module</TableHeaderCell>
                      <TableHeaderCell className="text-right">Events</TableHeaderCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.module_breakdown.map((m) => (
                      <TableRow key={m.label}>
                        <TableCell className="capitalize">{m.label.replace(/_/g, ' ')}</TableCell>
                        <TableCell className="text-right font-mono">{m.count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-[var(--color-text-faint)] py-6 text-center">
                  No module activity in this range.
                </p>
              )}
            </Card>

            <Card className="p-5">
              <h2 className="text-sm font-medium text-[var(--color-text-primary)] mb-4">Tasks by priority</h2>
              {isLoading ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-9 rounded-lg bg-[var(--color-surface-hover)] animate-pulse" />
                  ))}
                </div>
              ) : data && data.tasks.total > 0 ? (
                <>
                  <div className="flex items-center gap-4 mb-4 text-xs text-[var(--color-text-muted)]">
                    <span>{data.tasks.total} total</span>
                    <span>{data.tasks.open} open</span>
                    <span>{data.tasks.resolved} resolved</span>
                  </div>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableHeaderCell>Priority</TableHeaderCell>
                        <TableHeaderCell className="text-right">Count</TableHeaderCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.tasks.by_priority.map((p) => (
                        <TableRow key={p.label}>
                          <TableCell className="capitalize">{p.label}</TableCell>
                          <TableCell className="text-right font-mono">{p.count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </>
              ) : (
                <p className="text-sm text-[var(--color-text-faint)] py-6 text-center">
                  No tasks created in this range.
                </p>
              )}
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Workflow size={14} className="text-[var(--color-text-faint)]" />
                <span className="text-xs text-[var(--color-text-muted)]">
                  {data?.workflows.active_workflows ?? 0} of {data?.workflows.total_workflows ?? 0} workflows active
                  {data?.workflows.success_rate != null && ` — ${data.workflows.success_rate}% success rate`}
                </span>
              </div>
              <BreakdownTable
                title="Workflow runs by status"
                items={data?.workflows.by_status ?? []}
                emptyLabel="No workflow runs in this range."
              />
            </div>

            <div>
              <div className="flex items-center gap-2 mb-3">
                <GitCommitHorizontal size={14} className="text-[var(--color-text-faint)]" />
                <span className="text-xs text-[var(--color-text-muted)]">
                  {data?.commit_scheduler.active_jobs ?? 0} of {data?.commit_scheduler.total_jobs ?? 0} jobs active
                  {data?.commit_scheduler.success_rate != null && ` — ${data.commit_scheduler.success_rate}% success rate`}
                </span>
              </div>
              <BreakdownTable
                title="Commit runs by status"
                items={data?.commit_scheduler.by_status ?? []}
                emptyLabel="No commit runs in this range."
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
