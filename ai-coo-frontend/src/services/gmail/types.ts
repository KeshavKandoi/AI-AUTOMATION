export interface GmailEmail {
  from: string | null
  subject: string | null
  snippet: string | null
}

export interface GmailUnreadResult {
  unread_count: number
  emails: GmailEmail[]
}

export interface GmailService {
  getUnread(orgId: string): Promise<GmailUnreadResult>
  getSummary(orgId: string): Promise<string>
}
