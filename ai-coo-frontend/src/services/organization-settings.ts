import { apiClient } from '@/api/client'

export interface DiscordWebhookSettings {
  configured: boolean
  masked_url: string | null
  source: 'settings' | 'environment' | null
}

export const organizationSettingsService = {
  getDiscordWebhook: () =>
    apiClient.get<DiscordWebhookSettings>('/organization-settings/discord-webhook').then((response) => response.data),

  saveDiscordWebhook: (webhookUrl: string | null) =>
    apiClient.put<DiscordWebhookSettings>('/organization-settings/discord-webhook', { webhook_url: webhookUrl }).then((response) => response.data),
}
