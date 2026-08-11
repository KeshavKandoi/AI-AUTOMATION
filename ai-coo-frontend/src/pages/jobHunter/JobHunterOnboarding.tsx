import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle } from 'lucide-react'
import { jobHunterService } from '@/services/jobHunter'
import type { ExperienceLevel, JobHunterPreferencesOut, ProjectHighlight } from '@/services/jobHunter'
import Card from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import TagInput from '@/components/ui/TagInput'

// Exact values documented on backend/job_hunter/schemas.py — the backend
// stores these as unconstrained list[str] (not an enum), but these are the
// literal values the field comments specify. Do not diverge from these.
const EMPLOYMENT_TYPES = ['Internship', 'Full-time', 'Part-time', 'Contract', 'Freelance']
const WORK_MODES = ['Remote', 'Hybrid', 'Onsite']

function labelClass() {
  return 'text-sm font-medium text-[var(--color-text-muted)]'
}
function selectClass() {
  return 'w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)]'
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[var(--color-alert-dim)] bg-[var(--color-alert-dim)] px-3 py-2 text-xs text-[var(--color-alert)]">
      <AlertCircle size={14} className="shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  )
}

interface JobHunterOnboardingProps {
  existing: JobHunterPreferencesOut | null
  onSaved: () => void
}

export default function JobHunterOnboarding({ existing, onSaved }: JobHunterOnboardingProps) {
  const isEdit = !!existing
  const queryClient = useQueryClient()

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>('fresher')
  const [yearsOfExperience, setYearsOfExperience] = useState('')
  const [currentDesignation, setCurrentDesignation] = useState('')
  const [currentCompany, setCurrentCompany] = useState('')
  const [employmentTypes, setEmploymentTypes] = useState<string[]>([])
  const [workModes, setWorkModes] = useState<string[]>([])
  const [desiredRoles, setDesiredRoles] = useState<string[]>([])
  const [skills, setSkills] = useState<string[]>([])
  const [preferredLocations, setPreferredLocations] = useState<string[]>([])
  const [salaryMin, setSalaryMin] = useState('')
  const [salaryMax, setSalaryMax] = useState('')
  const [salaryCurrency, setSalaryCurrency] = useState('INR')
  const [projectHighlights, setProjectHighlights] = useState<ProjectHighlight[]>([])

  useEffect(() => {
    if (existing) {
      setFullName(existing.full_name)
      setEmail(existing.email)
      setExperienceLevel(existing.experience_level as ExperienceLevel)
      setYearsOfExperience(existing.years_of_experience?.toString() ?? '')
      setCurrentDesignation(existing.current_designation ?? '')
      setCurrentCompany(existing.current_company ?? '')
      setEmploymentTypes(existing.employment_types)
      setWorkModes(existing.work_modes)
      setDesiredRoles(existing.desired_roles)
      setSkills(existing.skills)
      setPreferredLocations(existing.preferred_locations)
      setSalaryMin(existing.expected_salary_min?.toString() ?? '')
      setSalaryMax(existing.expected_salary_max?.toString() ?? '')
      setSalaryCurrency(existing.salary_currency ?? 'INR')
      setProjectHighlights(existing.project_highlights)
    }
  }, [existing])

  function toggleInList(list: string[], setList: (v: string[]) => void, item: string) {
    setList(list.includes(item) ? list.filter((i) => i !== item) : [...list, item])
  }

  function addHighlight() {
    setProjectHighlights([...projectHighlights, { title: '', description: '' }])
  }
  function updateHighlight(index: number, field: keyof ProjectHighlight, value: string) {
    setProjectHighlights(
      projectHighlights.map((h, i) => (i === index ? { ...h, [field]: value } : h))
    )
  }
  function removeHighlight(index: number) {
    setProjectHighlights(projectHighlights.filter((_, i) => i !== index))
  }

  const buildPayload = () => ({
    full_name: fullName,
    email,
    experience_level: experienceLevel,
    years_of_experience: yearsOfExperience ? Number(yearsOfExperience) : undefined,
    current_designation: currentDesignation || undefined,
    current_company: currentCompany || undefined,
    employment_types: employmentTypes,
    work_modes: workModes,
    desired_roles: desiredRoles,
    skills,
    project_highlights: projectHighlights.filter((h) => h.title.trim() || h.description.trim()),
    preferred_locations: preferredLocations,
    expected_salary_min: salaryMin ? Number(salaryMin) : undefined,
    expected_salary_max: salaryMax ? Number(salaryMax) : undefined,
    salary_currency: salaryCurrency || undefined,
  })

  const saveMutation = useMutation({
    mutationFn: () =>
      isEdit
        ? jobHunterService.updatePreferences(buildPayload())
        : jobHunterService.savePreferences(buildPayload()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-hunter', 'preferences'] })
      onSaved()
    },
  })

  const canSubmit =
    fullName.trim() &&
    email.trim() &&
    desiredRoles.length > 0 &&
    skills.length > 0 &&
    preferredLocations.length > 0 &&
    employmentTypes.length > 0 &&
    workModes.length > 0

  return (
    <div className="p-6 md:p-8 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
          {isEdit ? 'Edit Job Hunter preferences' : 'Set up Job Hunter'}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          {isEdit
            ? 'Update your profile and search preferences.'
            : "Tell us what you're looking for and we'll start discovering matching jobs."}
        </p>
      </div>

      <Card className="p-6 flex flex-col gap-5">
        <div className="grid grid-cols-2 gap-3">
          <Input label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="flex flex-col gap-1.5">
            <label className={labelClass()}>Experience level</label>
            <select
              value={experienceLevel}
              onChange={(e) => setExperienceLevel(e.target.value as ExperienceLevel)}
              className={selectClass()}
            >
              <option value="student">Student</option>
              <option value="fresher">Fresher</option>
              <option value="experienced">Experienced</option>
            </select>
          </div>
          <Input
            label="Years of experience"
            type="number"
            step="0.5"
            min="0"
            value={yearsOfExperience}
            onChange={(e) => setYearsOfExperience(e.target.value)}
          />
          <Input
            label="Current designation"
            value={currentDesignation}
            onChange={(e) => setCurrentDesignation(e.target.value)}
          />
        </div>

        <Input
          label="Current company (optional)"
          value={currentCompany}
          onChange={(e) => setCurrentCompany(e.target.value)}
        />

        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Employment types</label>
          <div className="flex flex-wrap gap-2">
            {EMPLOYMENT_TYPES.map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => toggleInList(employmentTypes, setEmploymentTypes, type)}
                className={
                  employmentTypes.includes(type)
                    ? 'rounded-lg border border-[var(--color-signal)] bg-[var(--color-signal-dim)] text-[var(--color-signal)] px-3 py-1.5 text-xs'
                    : 'rounded-lg border border-[var(--color-border)] text-[var(--color-text-muted)] px-3 py-1.5 text-xs hover:border-[var(--color-border-hover)]'
                }
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className={labelClass()}>Work modes</label>
          <div className="flex flex-wrap gap-2">
            {WORK_MODES.map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => toggleInList(workModes, setWorkModes, mode)}
                className={
                  workModes.includes(mode)
                    ? 'rounded-lg border border-[var(--color-signal)] bg-[var(--color-signal-dim)] text-[var(--color-signal)] px-3 py-1.5 text-xs'
                    : 'rounded-lg border border-[var(--color-border)] text-[var(--color-text-muted)] px-3 py-1.5 text-xs hover:border-[var(--color-border-hover)]'
                }
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <TagInput
          label="Desired roles"
          value={desiredRoles}
          onChange={setDesiredRoles}
          placeholder="e.g. Backend Engineer — type and press Enter"
        />
        <TagInput
          label="Skills"
          value={skills}
          onChange={setSkills}
          placeholder="e.g. Python — type and press Enter"
        />
        <TagInput
          label="Preferred locations"
          value={preferredLocations}
          onChange={setPreferredLocations}
          placeholder="e.g. Bengaluru — type and press Enter"
        />

        <div className="grid grid-cols-3 gap-3">
          <Input
            label="Min expected salary"
            type="number"
            value={salaryMin}
            onChange={(e) => setSalaryMin(e.target.value)}
          />
          <Input
            label="Max expected salary"
            type="number"
            value={salaryMax}
            onChange={(e) => setSalaryMax(e.target.value)}
          />
          <Input
            label="Currency"
            value={salaryCurrency}
            onChange={(e) => setSalaryCurrency(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className={labelClass()}>Project highlights (optional)</label>
            <button
              type="button"
              onClick={addHighlight}
              className="text-xs text-[var(--color-signal)] hover:underline"
            >
              + Add highlight
            </button>
          </div>
          {projectHighlights.map((h, i) => (
            <div key={i} className="rounded-lg border border-[var(--color-border)] p-3 flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Project title"
                  value={h.title}
                  onChange={(e) => updateHighlight(i, 'title', e.target.value)}
                  className="flex-1"
                />
                <button
                  type="button"
                  onClick={() => removeHighlight(i)}
                  className="text-[var(--color-text-faint)] hover:text-[var(--color-alert)] text-xs shrink-0"
                >
                  Remove
                </button>
              </div>
              <textarea
                placeholder="Brief description"
                value={h.description}
                onChange={(e) => updateHighlight(i, 'description', e.target.value)}
                rows={2}
                className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-signal)] focus:ring-1 focus:ring-[var(--color-signal)] resize-none"
              />
            </div>
          ))}
        </div>

        {saveMutation.isError && (
          <ErrorBanner
            message={
              (saveMutation.error as { response?: { data?: { detail?: string } } })?.response?.data
                ?.detail ?? 'Something went wrong. Please check the fields and try again.'
            }
          />
        )}

        <Button
          className="w-full"
          disabled={!canSubmit}
          loading={saveMutation.isPending}
          onClick={() => saveMutation.mutate()}
        >
          {isEdit ? 'Save changes' : 'Complete setup & start discovering jobs'}
        </Button>
      </Card>
    </div>
  )
}
