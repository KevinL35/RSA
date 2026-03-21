import { apiGetJson } from '../../shared/services/api'

export type AuditLogRow = {
  id: string
  username: string
  menu_key: string
  message: string
  detail: Record<string, unknown> | null
  created_at: string
}

export type AuditLogListResponse = {
  items: AuditLogRow[]
  total: number
  limit: number
  offset: number
}

export function fetchAuditLogs(params: { limit?: number; offset?: number }) {
  const sp = new URLSearchParams()
  if (params.limit != null) sp.set('limit', String(params.limit))
  if (params.offset != null) sp.set('offset', String(params.offset))
  const q = sp.toString()
  return apiGetJson<AuditLogListResponse>(`/api/v1/audit-logs${q ? `?${q}` : ''}`)
}
