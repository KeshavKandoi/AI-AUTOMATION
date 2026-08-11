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
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (days <= 0) return 'today'
  if (days === 1) return '1 day ago'
  if (days < 30) return `${days} days ago`
  const months = Math.floor(days / 30)
  return months === 1 ? '1 month ago' : `${months} months ago`
}

export default function JobDiscovery() {
  const queryClient = useQueryClient()

  const [searchDraft, setSearchDraft] = useState('')
  const [appliedSearch, setAppliedSearch] = useState('')
  const [employmentType, setEmploymentType] = useState('')
  const [workMode, setWorkMode] = useState('')
  const [offset, setOffset] = useState(0)
  const [selectedJob, setSelectedJob] = useState<JobOut | null>(null)

  const filters: JobListFilters = useMemo(
    () => ({
      employment_type: employmentType || undefined,
      work_mode: workMode || undefined,
      search: appliedSearch || undefined,
    }),
    [employmentType, workMode, appliedSearch]
  )

  useEffect(() => {
    setOffset(0)
  }, [employmentType, workMode, appliedSearch])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['job-hunter', 'jobs', filters, offset],
    queryFn: () => jobHunterService.listJobs(PAGE_SIZE, offset, filters),
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

  const hasFilters = !!(employmentType || workMode || appliedSearch)
  const total = data?.total ?? 0
  const items = data?.items ?? []
  const rangeStart = total === 0 ? 0 : offset + 1
  const rangeEnd = Math.min(offset + PAGE_SIZE, total)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex-1 min-w-[240px]">
          <p className="text-sm text-[var(--color-text-muted)]">
            {total > 0 ? `${total} matching jobs discovered so far` : 'Run a search to discover matching jobs'}
          </p>
        </div>
        <Button
          variant="secondary"
          loading={runSearchMutation.isPending}
          disabled={runSearchMutation.isPending}
          onClick={() => runSearchMutation.mutate()}
        >
          <RefreshCw size={14} className={runSearchMutation.isPending ? 'animate-spin' : ''} />
          Run search
        </Button>
      </div>

      {runSearchMutation.isSuccess && !runSearchMutation.isPending && (
        <div className="rounded-lg border border-[var(--color-signal-dim)] bg-[var(--color-signal-dim)] px-3 py-2 text-xs text-[var(--color-signal)]">
          {runSearchMutation.data.skipped
            ? "Search skipped - " + (runSearchMutation.data.reason ?? "already running or too recent")
            : "Search complete - " + (runSearchMutation.data.jobs_new ?? 0) + " new job" +
              ((runSearchMutation.data.jobs_new ?? 0) === 1 ? "" : "s") +
              " found (" + (runSearchMutation.data.jobs_found ?? 0) + " total matched)"}
        </div>
      )}
      {runSearchMutation.isError && <ErrorBanner message="Couldn't trigger a search run. Please try again." />}

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
              placeholder="Search job title, company, skills..."
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
          {hasFilters && (
            <Button variant="ghost" onClick={clearFilters}>
              Clear
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
            title={hasFilters ? 'No jobs match these filters' : 'No jobs discovered yet'}
            description={
              hasFilters
                ? 'Try widening your filters or clearing them.'
                : 'Run a search to start discovering roles that match your preferences.'
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
