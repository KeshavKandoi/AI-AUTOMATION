import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Briefcase,
  Building2,
  CheckCircle2,
  Clock,
  ExternalLink,
  MapPin,
  RefreshCw,
  Search,
  Sparkles,
  Wallet,
} from 'lucide-react'
import { jobHunterService } from '@/services/jobHunter'
import type { JobListFilters, JobOut } from '@/services/jobHunter'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import Badge from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'

// Same literal values documented on backend/job_hunter/schemas.py used by
// the onboarding form — kept as a local copy since JobHunterOnboarding
// doesn't export them.
const EMPLOYMENT_TYPES = ['Internship', 'Full-time', 'Part-time', 'Contract', 'Freelance']
const WORK_MODES = ['Remote', 'Hybrid', 'Onsite']
const PAGE_SIZE = 20

type ViewMode = 'for_you' | 'all'

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

function formatSalary(job: JobOut): string | null {
  if (job.salary_min == null && job.salary_max == null) return null
  const currency = job.salary_currency ?? ''
  const fmt = (n: number) => n.toLocaleString()
  if (job.salary_min != null && job.salary_max != null) {
    return `${currency} ${fmt(job.salary_min)} - ${fmt(job.salary_max)}`.trim()
  }
  if (job.salary_min != null) return `${currency} ${fmt(job.salary_min)}+`.trim()
  return `Up to ${currency} ${fmt(job.salary_max as number)}`.trim()
}

function timeAgo(iso: string | null): string {
  if (!iso) return ''
  const diffMs = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diffMs / (1000 * 60))
  const hours = Math.floor(diffMs / (1000 * 60 * 60))
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days === 1) return '1 day ago'
  if (days < 30) return `${days} days ago`
  const months = Math.floor(days / 30)
  return months === 1 ? '1 month ago' : `${months} months ago`
}

export default function JobDiscovery() {
  const queryClient = useQueryClient()

  const [viewMode, setViewMode] = useState<ViewMode>('for_you')
  const [searchDraft, setSearchDraft] = useState('')
  const [appliedSearch, setAppliedSearch] = useState('')
  const [employmentType, setEmploymentType] = useState('')
  const [workMode, setWorkMode] = useState('')
  const [offset, setOffset] = useState(0)
  const [selectedJob, setSelectedJob] = useState<JobOut | null>(null)

  // Preferences power "For You" — the user's saved desired_roles/skills
  // become the base personalization, applied as a DB-only query-time
  // filter (never scraping). They never need to re-type this in Discover.
  const { data: prefsData } = useQuery({
    queryKey: ['job-hunter', 'preferences'],
    queryFn: () => jobHunterService.getPreferences(),
  })
  const preferences = prefsData?.preferences

  const { data: lastSync } = useQuery({
    queryKey: ['job-hunter', 'last-sync'],
    queryFn: () => jobHunterService.getLastSync(),
    refetchInterval: 60_000,
  })

  const filters: JobListFilters = useMemo(() => {
    const base: JobListFilters = {
      employment_type: employmentType || undefined,
      work_mode: workMode || undefined,
      search: appliedSearch || undefined,
    }
    if (viewMode === 'for_you' && preferences) {
      return {
        ...base,
        roles: preferences.desired_roles?.length ? preferences.desired_roles : undefined,
        skills: preferences.skills?.length ? preferences.skills : undefined,
      }
    }
    return base
  }, [viewMode, preferences, employmentType, workMode, appliedSearch])

  useEffect(() => {
    setOffset(0)
  }, [viewMode, employmentType, workMode, appliedSearch])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['job-hunter', 'jobs', filters, offset],
    queryFn: () => jobHunterService.listJobs(PAGE_SIZE, offset, filters),
    // For You depends on preferences having loaded first, so its filter
    // is correct on the very first fetch rather than briefly showing
    // unfiltered results.
    enabled: viewMode === 'all' || prefsData !== undefined,
  })

  const { data: applications } = useQuery({
    queryKey: ['job-hunter', 'applications'],
    queryFn: () => jobHunterService.listApplications(),
  })
  const savedJobIds = useMemo(
    () => new Set((applications ?? []).map((a) => a.job_id)),
    [applications]
  )

  const runSearchMutation = useMutation({
    mutationFn: () => jobHunterService.runSearchNow(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-hunter', 'jobs'] })
      queryClient.invalidateQueries({ queryKey: ['job-hunter', 'last-sync'] })
    },
  })

  const saveMutation = useMutation({
    mutationFn: (jobId: string) => jobHunterService.createApplication(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-hunter', 'applications'] })
    },
  })

  const clearFilters = () => {
    setSearchDraft('')
    setAppliedSearch('')
    setEmploymentType('')
    setWorkMode('')
  }

  const hasTempFilters = !!(employmentType || workMode || appliedSearch)
  const total = data?.total ?? 0
  const items = data?.items ?? []
  const rangeStart = total === 0 ? 0 : offset + 1
  const rangeEnd = Math.min(offset + PAGE_SIZE, total)
  const hasPreferences = !!(preferences?.desired_roles?.length || preferences?.skills?.length)

  return (
    <div className="flex flex-col gap-5">
      {/* Header: view toggle + last-synced indicator (replaces the old
          prominent "Run search" primary action — the six-hour background
          sweep keeps the database fresh automatically; a manual refresh
          is now a small secondary action further down). */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-1">
          <button
            onClick={() => setViewMode('for_you')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === 'for_you'
                ? 'bg-[var(--color-signal-dim)] text-[var(--color-signal)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
            }`}
          >
            <Sparkles size={13} />
            For You
          </button>
          <button
            onClick={() => setViewMode('all')}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === 'all'
                ? 'bg-[var(--color-signal-dim)] text-[var(--color-signal)]'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
            }`}
          >
            All Jobs
          </button>
        </div>

        <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
          <span>
            {lastSync?.last_synced_at
              ? `Last synced ${timeAgo(lastSync.last_synced_at)}`
              : 'Not synced yet'}
          </span>
          <Button
            variant="ghost"
            className="text-xs"
            loading={runSearchMutation.isPending}
            disabled={runSearchMutation.isPending}
            onClick={() => runSearchMutation.mutate()}
          >
            <RefreshCw size={12} className={runSearchMutation.isPending ? 'animate-spin' : ''} />
            Refresh jobs
          </Button>
        </div>
      </div>

      {viewMode === 'for_you' && !hasPreferences && (
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-xs text-[var(--color-text-muted)]">
          Add desired roles or skills in Preferences to personalize this view — showing the full database inventory for now.
        </div>
      )}

      <div className="flex-1 min-w-[240px]">
        <p className="text-sm text-[var(--color-text-muted)]">
          {total > 0
            ? `${total} ${viewMode === 'for_you' ? 'matching' : ''} job${total === 1 ? '' : 's'} in the database`
            : 'No jobs found — the background sweep refreshes the database every 6 hours'}
        </p>
      </div>

      {runSearchMutation.isSuccess && !runSearchMutation.isPending && (
        <div className="rounded-lg border border-[var(--color-signal-dim)] bg-[var(--color-signal-dim)] px-3 py-2 text-xs text-[var(--color-signal)]">
          {runSearchMutation.data.status === "already_running"
            ? "A sync is already running for your account - check back shortly."
            : "Sync started - this runs in the background and can take a while; the database updates as it goes."}
        </div>
      )}
      {runSearchMutation.isError && <ErrorBanner message="Couldn't trigger a refresh. Please try again." />}

      <Card className="p-4 flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          <div className="flex-1 min-w-[200px] flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3">
            <Search size={14} className="text-[var(--color-text-faint)] shrink-0" />
            <input
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') setAppliedSearch(searchDraft.trim())
              }}
              placeholder={viewMode === 'for_you' ? 'Narrow your matches further...' : 'Search job title, company, skills...'}
              className="flex-1 bg-transparent text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none py-2.5"
            />
          </div>
          <select value={employmentType} onChange={(e) => setEmploymentType(e.target.value)} className={selectClass()}>
            <option value="">Any employment type</option>
            {EMPLOYMENT_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <select value={workMode} onChange={(e) => setWorkMode(e.target.value)} className={selectClass()}>
            <option value="">Any work mode</option>
            {WORK_MODES.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <Button variant="secondary" onClick={() => setAppliedSearch(searchDraft.trim())}>
            Search
          </Button>
          {hasTempFilters && (
            <Button variant="ghost" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </div>
      </Card>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : isError ? (
        <Card className="p-6">
          <ErrorBanner message="Couldn't load jobs." />
          <Button variant="ghost" className="mt-3" onClick={() => refetch()}>
            Retry
          </Button>
        </Card>
      ) : items.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            icon={Briefcase}
            title={hasTempFilters ? 'No jobs match these filters' : 'No jobs found'}
            description={
              hasTempFilters
                ? 'Try widening your filters or clearing them.'
                : viewMode === 'for_you'
                  ? 'No jobs currently match your saved preferences. Try All Jobs, or update your Preferences.'
                  : 'The background sweep refreshes the database automatically every 6 hours.'
            }
          />
        </Card>
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {items.map((job) => {
              const salary = formatSalary(job)
              const isSaved = savedJobIds.has(job.id)
              return (
                <Card
                  key={job.id}
                  className="p-5 cursor-pointer hover:border-[var(--color-border-hover)] transition-colors"
                  onClick={() => setSelectedJob(job)}
                >
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">{job.job_title}</h3>
                        {isSaved && (
                          <Badge tone="signal">
                            <CheckCircle2 size={11} className="mr-1 inline" />
                            In tracker
                          </Badge>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-[var(--color-text-muted)]">
                        <span className="flex items-center gap-1">
                          <Building2 size={12} />
                          {job.company_name}
                        </span>
                        {job.location && (
                          <span className="flex items-center gap-1">
                            <MapPin size={12} />
                            {job.location}
                          </span>
                        )}
                        {salary && (
                          <span className="flex items-center gap-1">
                            <Wallet size={12} />
                            {salary}
                          </span>
                        )}
                        {job.posted_at && (
                          <span className="flex items-center gap-1">
                            <Clock size={12} />
                            {timeAgo(job.posted_at)}
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {job.employment_type && <Badge tone="neutral">{job.employment_type}</Badge>}
                        {job.work_mode && <Badge tone="neutral">{job.work_mode}</Badge>}
                        {job.sources.length > 0 && (
                          <Badge tone="neutral">via {job.sources[0].platform}</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>

          <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
            <span>{total > 0 ? `Showing ${rangeStart}-${rangeEnd} of ${total}` : ''}</span>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
              >
                Previous
              </Button>
              <Button
                variant="ghost"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}

      <Modal open={!!selectedJob} onClose={() => setSelectedJob(null)} title={selectedJob?.job_title} className="max-w-2xl">
        {selectedJob && (
          <div className="flex flex-col gap-4 max-h-[70vh] overflow-y-auto pr-1">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[var(--color-text-muted)]">
              <span className="flex items-center gap-1">
                <Building2 size={13} />
                {selectedJob.company_name}
              </span>
              {selectedJob.location && (
                <span className="flex items-center gap-1">
                  <MapPin size={13} />
                  {selectedJob.location}
                </span>
              )}
              {formatSalary(selectedJob) && (
                <span className="flex items-center gap-1">
                  <Wallet size={13} />
                  {formatSalary(selectedJob)}
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-1.5">
              {selectedJob.employment_type && <Badge tone="neutral">{selectedJob.employment_type}</Badge>}
              {selectedJob.work_mode && <Badge tone="neutral">{selectedJob.work_mode}</Badge>}
              {selectedJob.experience_required && <Badge tone="neutral">{selectedJob.experience_required}</Badge>}
            </div>

            {selectedJob.description && (
              <div>
                <h4 className="text-xs font-medium text-[var(--color-text-muted)] mb-1">Description</h4>
                <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">{selectedJob.description}</p>
              </div>
            )}
            {selectedJob.responsibilities && (
              <div>
                <h4 className="text-xs font-medium text-[var(--color-text-muted)] mb-1">Responsibilities</h4>
                <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">{selectedJob.responsibilities}</p>
              </div>
            )}
            {selectedJob.required_skills.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-[var(--color-text-muted)] mb-1">Required skills</h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedJob.required_skills.map((s) => (
                    <Badge key={s} tone="neutral">{s}</Badge>
                  ))}
                </div>
              </div>
            )}
            {selectedJob.qualifications && (
              <div>
                <h4 className="text-xs font-medium text-[var(--color-text-muted)] mb-1">Qualifications</h4>
                <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">{selectedJob.qualifications}</p>
              </div>
            )}
            {selectedJob.benefits && (
              <div>
                <h4 className="text-xs font-medium text-[var(--color-text-muted)] mb-1">Benefits</h4>
                <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">{selectedJob.benefits}</p>
              </div>
            )}
            {selectedJob.company_info && (
              <div>
                <h4 className="text-xs font-medium text-[var(--color-text-muted)] mb-1">About the company</h4>
                <p className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap">{selectedJob.company_info}</p>
              </div>
            )}

            {selectedJob.sources.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-[var(--color-text-muted)] mb-1">Sources</h4>
                <div className="flex flex-col gap-1">
                  {selectedJob.sources.map((s) => (
                    <a
                      key={s.id}
                      href={s.platform_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 text-xs text-[var(--color-signal)] hover:underline"
                    >
                      {s.platform}
                      <ExternalLink size={11} />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {saveMutation.isError && <ErrorBanner message="Couldn't save this job to your tracker." />}

            <div className="flex items-center gap-2 pt-2 border-t border-[var(--color-border)]">
              <a href={selectedJob.original_apply_url} target="_blank" rel="noreferrer" className="flex-1">
                <Button variant="secondary" className="w-full">
                  <ExternalLink size={14} />
                  Apply on original site
                </Button>
              </a>
              {savedJobIds.has(selectedJob.id) ? (
                <Button variant="ghost" disabled className="flex-1">
                  <CheckCircle2 size={14} />
                  Already in tracker
                </Button>
              ) : (
                <Button
                  className="flex-1"
                  loading={saveMutation.isPending && saveMutation.variables === selectedJob.id}
                  disabled={saveMutation.isPending}
                  onClick={() => saveMutation.mutate(selectedJob.id)}
                >
                  Save to tracker
                </Button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
