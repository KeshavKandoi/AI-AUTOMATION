import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bookmark, Building2, ExternalLink, MapPin, Trash2 } from 'lucide-react'
import { jobHunterService } from '@/services/jobHunter'
import type { ApplicationRow } from '@/services/jobHunter'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'
import { Button } from '@/components/ui/Button'

function SavedJobCard({ row, onDelete, deleting }: { row: ApplicationRow; onDelete: () => void; deleting: boolean }) {
  const { data: job, isLoading } = useQuery({
    queryKey: ['job-hunter', 'job', row.job_id],
    queryFn: () => jobHunterService.getJob(row.job_id),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) return <Skeleton className="h-28 w-full" />
  if (!job) return null

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-base font-medium text-[var(--color-text-primary)]">{job.job_title}</h3>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-[var(--color-text-muted)]">
            <span className="inline-flex items-center gap-1.5"><Building2 size={14} />{job.company_name}</span>
            {job.location && <span className="inline-flex items-center gap-1.5"><MapPin size={14} />{job.location}</span>}
          </div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-[var(--color-text-muted)]">
            {job.employment_type && <span>{job.employment_type}</span>}
            {job.work_mode && <span>· {job.work_mode}</span>}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={job.original_apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm text-[var(--color-text-primary)] hover:border-[var(--color-signal)]"
          >
            View job <ExternalLink size={14} />
          </a>
          <button
            type="button"
            disabled={deleting}
            onClick={onDelete}
            aria-label={`Remove ${job.job_title} from saved jobs`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm text-[var(--color-alert)] hover:border-[var(--color-alert)] disabled:opacity-50"
          >
            <Trash2 size={14} /> Remove
          </button>
        </div>
      </div>
    </Card>
  )
}

export default function ApplicationTracker() {
  const queryClient = useQueryClient()
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['job-hunter', 'applications'],
    queryFn: () => jobHunterService.listApplications(),
  })
  const deleteMutation = useMutation({
    mutationFn: (applicationId: string) => jobHunterService.deleteSavedJob(applicationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['job-hunter', 'applications'] }),
  })

  const removeSavedJob = (row: ApplicationRow) => {
    if (window.confirm('Remove this job from your saved jobs?')) {
      deleteMutation.mutate(row.id)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Saved jobs</h2>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">Jobs you saved from Discover, ready to revisit when you choose.</p>
      </div>
      {deleteMutation.isError && <p className="text-sm text-[var(--color-alert)]">Could not remove that saved job. Please try again.</p>}
      {isLoading ? (
        <div className="flex flex-col gap-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-28 w-full" />)}</div>
      ) : isError ? (
        <Card className="p-6">
          <p className="text-sm text-[var(--color-alert)]">Saved jobs are temporarily unavailable.</p>
          <Button variant="ghost" className="mt-3" onClick={() => refetch()}>Retry</Button>
        </Card>
      ) : !data?.length ? (
        <Card className="p-8">
          <EmptyState icon={Bookmark} title="No saved jobs yet" description="Save a job in Discover to find it here later." />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">{data.map((row) => (
          <SavedJobCard
            key={row.id}
            row={row}
            onDelete={() => removeSavedJob(row)}
            deleting={deleteMutation.isPending && deleteMutation.variables === row.id}
          />
        ))}</div>
      )}
    </div>
  )
}
