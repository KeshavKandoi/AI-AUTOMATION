import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { GitBranch, Mail, Calendar as CalendarIcon, CheckCircle2, Circle, ShieldCheck } from 'lucide-react'
import { integrationsService, type IntegrationProvider } from '@/services/integrations'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/Button'

const PROVIDER_META: Record<IntegrationProvider, { label: string; description: string; icon: typeof GitBranch; dataUseNote?: string }> = {
  github: {
    label: 'GitHub',
    description: 'Sync issues, create commits, and manage repositories.',
    icon: GitBranch,
  },
  gmail: {
    label: 'Gmail',
    description: 'Scans recent mail to detect job-application replies and unread messages, and sends emails you configure in workflows.',
    icon: Mail,
    dataUseNote: 'Used only for Job Hunter tracking, AI task suggestions, and workflow emails you set up — never sold or used for ads.',
  },
  calendar: {
    label: 'Google Calendar',
    description: 'Views upcoming events and creates events for interviews and workflows you configure.',
    icon: CalendarIcon,
    dataUseNote: 'Used only to show upcoming events and create events you or your workflows request — never sold or used for ads.',
  },
}

const ALL_PROVIDERS: IntegrationProvider[] = ['github', 'gmail', 'calendar']

export default function Integrations() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()
  const [confirmingProvider, setConfirmingProvider] = useState<IntegrationProvider | null>(null)

  const { data: integrations, isLoading } = useQuery({
    queryKey: ['integrations', orgId],
    queryFn: () => integrationsService.list(orgId!),
    enabled: !!orgId,
  })

  const disconnectMutation = useMutation({
    mutationFn: (provider: IntegrationProvider) => integrationsService.disconnect(provider, orgId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrations', orgId] })
      setConfirmingProvider(null)
    },
  })

  const connectedByProvider = new Map((integrations ?? []).map((i) => [i.provider, i]))

  const handleConnect = async (provider: IntegrationProvider) => {
    if (!orgId) return
    const url = await integrationsService.getLoginUrl(provider)
    window.location.href = url
  }

  const handleDisconnectClick = (provider: IntegrationProvider) => {
    if (confirmingProvider === provider) {
      disconnectMutation.mutate(provider)
    } else {
      setConfirmingProvider(provider)
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-text-primary)]">
          Integrations
        </h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Connect services so your Workforge can act on your behalf
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {ALL_PROVIDERS.map((provider) => {
          const meta = PROVIDER_META[provider]
          const integration = connectedByProvider.get(provider)
          const isConnected = integration?.connected ?? false
          const isConfirming = confirmingProvider === provider
          const isDisconnecting = disconnectMutation.isPending && disconnectMutation.variables === provider

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

              {meta.dataUseNote && !isConnected && (
                <div className="flex items-start gap-1.5 text-[11px] text-[var(--color-text-faint)] leading-relaxed">
                  <ShieldCheck size={12} className="shrink-0 mt-0.5" />
                  <span>
                    {meta.dataUseNote}{' '}
                    <Link to="/privacy" className="text-[var(--color-signal)] hover:brightness-110 underline underline-offset-2">
                      Privacy Policy
                    </Link>
                  </span>
                </div>
              )}

              <div className="mt-auto flex gap-2">
                <Button
                  variant={isConnected ? 'secondary' : 'primary'}
                  onClick={() => handleConnect(provider)}
                  className="flex-1"
                >
                  {isConnected ? 'Reconnect' : 'Connect'}
                </Button>
                {isConnected && (
                  <Button
                    variant={isConfirming ? 'primary' : 'ghost'}
                    onClick={() => handleDisconnectClick(provider)}
                    onBlur={() => setConfirmingProvider(null)}
                    loading={isDisconnecting}
                    className={isConfirming ? '!bg-[var(--color-alert)] !text-white' : ''}
                  >
                    {isConfirming ? 'Confirm?' : 'Disconnect'}
                  </Button>
                )}
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
