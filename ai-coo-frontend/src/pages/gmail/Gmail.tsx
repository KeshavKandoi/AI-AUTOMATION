import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Mail, ShieldCheck } from 'lucide-react'
import { jobHunterService } from '@/services/jobHunter'
import Card from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

const inputClass =
  'w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm text-[var(--color-text-primary)]'

const CATEGORY_LABELS: Record<string, string> = {
  interview_invite: 'Interview invitation',
  assessment: 'Assessment',
  rejection: 'Rejection',
  offer: 'Offer',
  reschedule: 'Reschedule',
  withdrawal: 'Withdrawal',
  application_confirmation: 'Application confirmation',
  unmatched: 'Recruitment email, no confident application match',
  not_recruitment: 'Not a recruitment email',
}

export default function Gmail() {
  const [subject, setSubject] = useState('')
  const [sender, setSender] = useState('')
  const [body, setBody] = useState('')

  const mutation = useMutation({
    mutationFn: () => jobHunterService.importEmail({ subject, sender, body }),
    onSuccess: () => {
      setSubject('')
      setSender('')
      setBody('')
    },
  })

  const result = mutation.data

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto flex flex-col gap-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
          Import email
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Paste a recruiter or job email into Job Hunter. WorkForge does not access or read your Gmail inbox.
        </p>
      </div>

      <Card className="p-5 flex flex-col gap-3">
        <div className="flex items-center gap-2 text-xs text-[var(--color-text-faint)]">
          <ShieldCheck size={14} />
          <span>Only the text you paste here is processed. Gmail access is used only to send emails for workflows you configure.</span>
        </div>
        <input className={inputClass} placeholder="Sender (optional)" value={sender} onChange={(e) => setSender(e.target.value)} />
        <input className={inputClass} placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
        <textarea className={inputClass} rows={12} placeholder="Paste the email body" value={body} onChange={(e) => setBody(e.target.value)} />
        <div>
          <Button onClick={() => mutation.mutate()} disabled={!body.trim() || mutation.isPending}>
            <Mail size={14} className="mr-2" />
            {mutation.isPending ? 'Processing' : 'Import email'}
          </Button>
        </div>
      </Card>

      {mutation.isError && (
        <p className="text-sm text-[var(--color-alert)]">Could not process this email. Try again.</p>
      )}

      {result && (
        <Card className="p-5 flex flex-col gap-1 text-sm text-[var(--color-text-muted)]">
          {result.duplicate ? (
            <p>This email was already imported.</p>
          ) : (
            <>
              <p>Detected: {CATEGORY_LABELS[result.category ?? ''] ?? result.category}</p>
              <p>{result.application_id ? 'Matched to an application.' : 'No application was updated.'}</p>
              {result.applications_updated > 0 && <p>Application status updated.</p>}
              {result.calendar_action && <p>Calendar event {result.calendar_action}d.</p>}
            </>
          )}
        </Card>
      )}
    </div>
  )
}
