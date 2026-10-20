import { apiClient } from '@/api/client'

export interface DiscordWebhookSettings {
  configured: boolean
  masked_url: string | null
  source: 'settings' | 'environment' | null
}

export const organizationSettingsService = {
  getDiscordLoginUrl: () =>
    apiClient.get<{ url: string }>('/discord/login').then((response) => response.data.url),

  getDiscordWebhook: () =>
    apiClient.get<DiscordWebhookSettings>('/organization-settings/discord-webhook').then((response) => response.data),

  saveDiscordWebhook: (webhookUrl: string | null) =>
    apiClient.put<DiscordWebhookSettings>('/organization-settings/discord-webhook', { webhook_url: webhookUrl }).then((response) => response.data),
}
