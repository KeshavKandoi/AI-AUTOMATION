import { useQuery } from '@tanstack/react-query'
import { GitBranch, Mail, Calendar as CalendarIcon, CheckCircle2, Circle } from 'lucide-react'
import { integrationsService, type IntegrationProvider } from '@/services/integrations'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/Button'

const PROVIDER_META: Record<IntegrationProvider, { label: string; description: string; icon: typeof GitBranch }> = {
  github: {
    label: 'GitHub',
    description: 'Sync issues, create commits, and manage repositories.',
    icon: GitBranch,
  },
  gmail: {
    label: 'Gmail',
    description: 'Read unread mail and send emails on your behalf.',
    icon: Mail,
  },
  calendar: {
    label: 'Google Calendar',
    description: 'View events and schedule new ones automatically.',
    icon: CalendarIcon,
  },
}

const ALL_PROVIDERS: IntegrationProvider[] = ['github', 'gmail', 'calendar']

export default function Integrations() {
  const orgId = useAuthStore((s) => s.user?.organization_id)

  const { data: integrations, isLoading } = useQuery({
    queryKey: ['integrations', orgId],
    queryFn: () => integrationsService.list(orgId!),
    enabled: !!orgId,
  })

  const connectedByProvider = new Map((integrations ?? []).map((i) => [i.provider, i]))

  const handleConnect = (provider: IntegrationProvider) => {
    if (!orgId) return
    window.location.href = integrationsService.loginUrl(provider, orgId)
  }

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
          Integrations
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Connect services so your AI COO can act on your behalf
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {ALL_PROVIDERS.map((provider) => {
          const meta = PROVIDER_META[provider]
          const integration = connectedByProvider.get(provider)
          const isConnected = integration?.connected ?? false

          return (
            <Card key={provider} className="p-5 flex flex-col gap-4">
              <div className="flex items-start justify-between">
                <div className="h-10 w-10 rounded-xl bg-[var(--color-surface-hover)] flex items-center justify-center">
                  <meta.icon size={18} className="text-[var(--color-text-primary)]" />
                </div>
                {isLoading ? (
                  <Skeleton className="h-5 w-20" />
                ) : isConnected ? (
                  <span className="flex items-center gap-1.5 text-xs text-[var(--color-signal)]">
                    <CheckCircle2 size={13} />
                    Connected
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-faint)]">
                    <Circle size={13} />
                    Not connected
                  </span>
                )}
              </div>

              <div>
                <h3 className="text-sm font-medium text-[var(--color-text-primary)]">{meta.label}</h3>
                <p className="mt-1 text-xs text-[var(--color-text-faint)]">{meta.description}</p>
              </div>

              <Button
                variant={isConnected ? 'secondary' : 'primary'}
                onClick={() => handleConnect(provider)}
                className="mt-auto w-full"
              >
                {isConnected ? 'Reconnect' : 'Connect'}
              </Button>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
