export type MemoryCategory =
  | 'user_preference'
  | 'project'
  | 'repository'
  | 'workflow'
  | 'conversation'
  | 'integration'
  | 'knowledge'
  | 'custom'

export type MemoryImportance = 'low' | 'medium' | 'high' | 'critical'
export type MemoryStatusFilter = 'active' | 'archived' | 'all'

export interface MemoryEntry {
  id: string
  organization_id: string
  title: string | null
  content: string
  category: string | null
  tags: string[] | null
  source: string | null
  importance: string | null
  status: string | null
  pinned: boolean | null
  favorited: boolean | null
  user_id: string | null
  metadata: Record<string, unknown> | null
  access_count: number | null
  created_at: string
  updated_at: string | null
  last_accessed_at: string | null
  deleted_at: string | null
}

export interface MemoryListResponse {
  items: MemoryEntry[]
  total: number
  limit: number
  offset: number
}

export interface MemoryFilters {
  category?: string
  status?: MemoryStatusFilter
  importance?: MemoryImportance
  pinned?: boolean
  favorited?: boolean
  tags?: string
  search?: string
  sort_by?: 'created_at' | 'updated_at' | 'last_accessed_at' | 'importance' | 'title'
  sort_dir?: 'asc' | 'desc'
}

export interface MemoryFilterOptions {
  categories: string[]
  tags: string[]
}

export interface CreateMemoryPayload {
  organization_id: string
  title: string
  content: string
  category?: string
  tags?: string[]
  source?: string
  importance?: MemoryImportance
  metadata?: Record<string, unknown>
}

export interface UpdateMemoryPayload {
  title?: string
  content?: string
  category?: string
  tags?: string[]
  importance?: MemoryImportance
  metadata?: Record<string, unknown>
}

export interface MemoryService {
  list(orgId: string, limit?: number, offset?: number, filters?: MemoryFilters): Promise<MemoryListResponse>
  get(memoryId: string, orgId: string): Promise<MemoryEntry>
  create(payload: CreateMemoryPayload): Promise<MemoryEntry>
  update(memoryId: string, orgId: string, payload: UpdateMemoryPayload): Promise<MemoryEntry>
  access(memoryId: string, orgId: string): Promise<MemoryEntry>
  pin(memoryId: string, orgId: string): Promise<MemoryEntry>
  unpin(memoryId: string, orgId: string): Promise<MemoryEntry>
  favorite(memoryId: string, orgId: string): Promise<MemoryEntry>
  unfavorite(memoryId: string, orgId: string): Promise<MemoryEntry>
  archive(memoryId: string, orgId: string): Promise<MemoryEntry>
  restore(memoryId: string, orgId: string): Promise<MemoryEntry>
  remove(memoryId: string, orgId: string): Promise<void>
  getFilterOptions(orgId: string): Promise<MemoryFilterOptions>
  getRecent(orgId: string, limit?: number): Promise<MemoryEntry[]>
}
