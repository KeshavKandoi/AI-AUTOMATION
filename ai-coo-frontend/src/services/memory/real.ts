import { apiClient } from '@/api/client'
import type {
  CreateMemoryPayload,
  MemoryEntry,
  MemoryFilterOptions,
  MemoryListResponse,
  MemoryService,
  UpdateMemoryPayload,
} from './types'

export const realMemoryService: MemoryService = {
  list: (orgId, limit = 50, offset = 0, filters = {}) =>
    apiClient
      .get<MemoryListResponse>('/memory', { params: { org_id: orgId, limit, offset, ...filters } })
      .then((r) => r.data),

  get: (memoryId, orgId) =>
    apiClient.get<MemoryEntry>(`/memory/${memoryId}`, { params: { org_id: orgId } }).then((r) => r.data),

  create: (payload: CreateMemoryPayload) =>
    apiClient
      .post<{ status: string; memory: MemoryEntry }>('/memory', payload)
      .then((r) => r.data.memory),

  update: (memoryId, orgId, payload: UpdateMemoryPayload) =>
    apiClient
      .patch<{ status: string; memory: MemoryEntry }>(`/memory/${memoryId}`, payload, { params: { org_id: orgId } })
      .then((r) => r.data.memory),

  access: (memoryId, orgId) =>
    apiClient
      .post<{ status: string; memory: MemoryEntry }>(`/memory/${memoryId}/access`, undefined, { params: { org_id: orgId } })
      .then((r) => r.data.memory),

  pin: (memoryId, orgId) =>
    apiClient
      .post<{ status: string; memory: MemoryEntry }>(`/memory/${memoryId}/pin`, undefined, { params: { org_id: orgId } })
      .then((r) => r.data.memory),

  unpin: (memoryId, orgId) =>
    apiClient
      .post<{ status: string; memory: MemoryEntry }>(`/memory/${memoryId}/unpin`, undefined, { params: { org_id: orgId } })
      .then((r) => r.data.memory),

  favorite: (memoryId, orgId) =>
    apiClient
      .post<{ status: string; memory: MemoryEntry }>(`/memory/${memoryId}/favorite`, undefined, { params: { org_id: orgId } })
      .then((r) => r.data.memory),

  unfavorite: (memoryId, orgId) =>
    apiClient
      .post<{ status: string; memory: MemoryEntry }>(`/memory/${memoryId}/unfavorite`, undefined, { params: { org_id: orgId } })
      .then((r) => r.data.memory),

  archive: (memoryId, orgId) =>
    apiClient
      .post<{ status: string; memory: MemoryEntry }>(`/memory/${memoryId}/archive`, undefined, { params: { org_id: orgId } })
      .then((r) => r.data.memory),

  restore: (memoryId, orgId) =>
    apiClient
      .post<{ status: string; memory: MemoryEntry }>(`/memory/${memoryId}/restore`, undefined, { params: { org_id: orgId } })
      .then((r) => r.data.memory),

  remove: (memoryId, orgId) =>
    apiClient.delete(`/memory/${memoryId}`, { params: { org_id: orgId } }).then(() => undefined),

  getFilterOptions: (orgId) =>
    apiClient.get<MemoryFilterOptions>('/memory/filters', { params: { org_id: orgId } }).then((r) => r.data),

  getRecent: (orgId, limit = 5) =>
    apiClient.get<MemoryEntry[]>('/memory/recent', { params: { org_id: orgId, limit } }).then((r) => r.data),
}
