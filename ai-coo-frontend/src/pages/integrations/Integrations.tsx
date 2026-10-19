import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { GitBranch, Mail, Calendar as CalendarIcon, CheckCircle2, Circle, ShieldCheck, MessageCircle } from 'lucide-react'
import { integrationsService, type IntegrationProvider } from '@/services/integrations'
import { organizationSettingsService } from '@/services/organization-settings'
import { useAuthStore } from '@/store/authStore'
import Card from '@/components/ui/Card'
import Skeleton from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'

function discordApiError(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Could not update Discord. Please try again.'
}

const PROVIDER_META: Record<IntegrationProvider, { label: string; description: string; icon: typeof GitBranch; dataUseNote?: string }> = {
  github: {
    label: 'GitHub',
    description: 'Choose a GitHub account, then select which repository WorkForge can access.',
    icon: GitBranch,
  },
  gmail: {
    label: 'Gmail',
    description: 'Sends emails you configure in workflows. WorkForge does not read your Gmail inbox.',
    icon: Mail,
    dataUseNote: 'Used only to send workflow emails you set up — never sold or used for ads.',
  },
  calendar: {
    label: 'Google Calendar',
    description: 'Views upcoming events and creates events you request or approve through tasks.',
    icon: CalendarIcon,
    dataUseNote: 'Used only to show upcoming events and create events you request.',
  },
}

const ALL_PROVIDERS: IntegrationProvider[] = ['github', 'gmail', 'calendar']

export default function Integrations() {
  const orgId = useAuthStore((s) => s.user?.organization_id)
  const queryClient = useQueryClient()
  const [confirmingProvider, setConfirmingProvider] = useState<IntegrationProvider | null>(null)
  const [discordModalOpen, setDiscordModalOpen] = useState(false)
  const [discordWebhookDraft, setDiscordWebhookDraft] = useState('')
  const [confirmDiscordDisconnect, setConfirmDiscordDisconnect] = useState(false)

  const { data: integrations, isLoading } = useQuery({
    queryKey: ['integrations', orgId],
    queryFn: () => integrationsService.list(orgId!),
    enabled: !!orgId,
  })
  const discordStatus = useQuery({
    queryKey: ['organization-settings', 'discord-webhook', orgId],
    queryFn: organizationSettingsService.getDiscordWebhook,
    enabled: !!orgId,
  })
  const discordMutation = useMutation({
    mutationFn: organizationSettingsService.saveDiscordWebhook,
    onSuccess: (status) => {
      queryClient.setQueryData(['organization-settings', 'discord-webhook', orgId], status)
      queryClient.invalidateQueries({ queryKey: ['organization-settings', 'discord-webhook', orgId] })
      setDiscordWebhookDraft('')
      setConfirmDiscordDisconnect(false)
      setDiscordModalOpen(false)
    },
  })

  const closeDiscordModal = () => {
    if (discordMutation.isPending) return
    setDiscordModalOpen(false)
    setDiscordWebhookDraft('')
    setConfirmDiscordDisconnect(false)
    discordMutation.reset()
  }

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
          Connect services so WorkForge can act on your behalf
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
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-sm font-medium text-[var(--color-text-primary)]">{meta.label}</h3>
                </div>
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
                  {isConnected ? (provider === 'github' ? 'Switch account' : 'Reconnect') : 'Connect'}
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
        <Card className="p-5 flex flex-col gap-4">
          <div className="flex items-start justify-between">
            <div className="h-10 w-10 rounded-xl bg-[var(--color-surface-hover)] flex items-center justify-center">
              <MessageCircle size={18} className="text-[var(--color-text-primary)]" />
            </div>
            {discordStatus.isLoading && orgId ? (
              <Skeleton className="h-5 w-20" />
            ) : discordStatus.isError || !orgId ? (
              <span className="text-xs text-[var(--color-text-faint)]">Status unavailable</span>
            ) : discordStatus.data?.configured ? (
              <span className="flex items-center gap-1.5 text-xs text-[var(--color-signal)]">
                <CheckCircle2 size={13} /> Connected
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs text-[var(--color-text-faint)]">
                <Circle size={13} /> Not connected
              </span>
            )}
          </div>
          <div>
            <h3 className="text-sm font-medium text-[var(--color-text-primary)]">Discord</h3>
            <p className="mt-1 text-xs text-[var(--color-text-faint)]">
              Sends workflow notifications to your organization’s Discord webhook.
            </p>
            {discordStatus.data?.configured && (
              <p className="mt-2 text-xs text-[var(--color-text-faint)]">
                Managed via {discordStatus.data.source === 'environment' ? 'backend environment' : 'Integrations'}.
              </p>
            )}
          </div>
          <Button
            type="button"
            className="mt-auto"
            onClick={() => setDiscordModalOpen(true)}
          >
            {discordStatus.data?.configured ? 'Manage' : 'Configure'}
          </Button>
        </Card>
      </div>
      <Modal open={discordModalOpen} onClose={closeDiscordModal} title="Discord integration">
        <div className="flex flex-col gap-4">
          {discordStatus.isError ? (
            <p className="text-sm text-[var(--color-alert)]" role="alert">Discord status is unavailable. Refresh the page before changing this integration.</p>
          ) : discordStatus.data?.configured ? (
            <p className="text-sm text-[var(--color-text-muted)]" role="status">
              Connected via {discordStatus.data.source === 'environment' ? 'backend environment' : 'saved webhook'} · {discordStatus.data.masked_url}
            </p>
          ) : (
            <p className="text-sm text-[var(--color-text-muted)]" role="status">Not connected. Add a Discord webhook URL to enable workflow notifications.</p>
          )}
          {discordStatus.data?.source === 'environment' && (
            <p className="text-xs text-[var(--color-text-muted)]">
              This webhook is managed in the backend environment. To disconnect it, remove DISCORD_WEBHOOK_URL and DISCORD_ENV_ORG_ID from the backend environment and restart the service. You can save a different URL here to override it.
            </p>
          )}
          <form
            className="flex flex-col gap-3"
            onSubmit={(event) => {
              event.preventDefault()
              if (discordWebhookDraft.trim()) discordMutation.mutate(discordWebhookDraft)
            }}
          >
            <Input
              label="Discord webhook URL"
              type="url"
              autoComplete="off"
              value={discordWebhookDraft}
              onChange={(event) => setDiscordWebhookDraft(event.target.value)}
              placeholder="https://discord.com/api/webhooks/..."
            />
            {discordMutation.isError && <p className="text-xs text-[var(--color-alert)]" role="alert">{discordApiError(discordMutation.error)}</p>}
            <Button type="submit" loading={discordMutation.isPending} disabled={!discordWebhookDraft.trim() || discordStatus.isError}>
              Save webhook
            </Button>
          </form>
          {discordStatus.data?.source === 'settings' && (
            <div className="border-t border-[var(--color-border)] pt-4 flex flex-col gap-2">
              <p className="text-xs text-[var(--color-text-muted)]">Disconnect removes the saved webhook. If an environment fallback is configured for this organization, it will become active.</p>
              {confirmDiscordDisconnect ? (
                <div className="flex gap-2">
                  <Button type="button" variant="secondary" loading={discordMutation.isPending} onClick={() => discordMutation.mutate(null)}>Confirm disconnect</Button>
                  <Button type="button" variant="ghost" onClick={() => setConfirmDiscordDisconnect(false)}>Cancel</Button>
                </div>
              ) : (
                <Button type="button" variant="secondary" onClick={() => setConfirmDiscordDisconnect(true)}>Disconnect</Button>
              )}
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
