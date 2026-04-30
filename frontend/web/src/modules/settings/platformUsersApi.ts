import { apiDeleteJson, apiGetJson, apiPatchJson, apiPostJson } from '../../shared/services/api'

export type PlatformUserRow = {
  id: string
  username: string
  status: string
  menu_keys: string[]
  created_at: string
}

export type PlatformUserListResponse = {
  items: PlatformUserRow[]
}

export type PlatformLoginResponse = {
  username: string
  role: string
  menu_keys: string[]
  token: string
}

export function fetchPlatformUsers() {
  return apiGetJson<PlatformUserListResponse>('/api/v1/platform-users')
}

export function createPlatformUser(body: {
  username: string
  password: string
  menu_keys: string[]
  status: 'active' | 'disabled'
}) {
  return apiPostJson<PlatformUserRow>('/api/v1/platform-users', body)
}

export function updatePlatformUser(
  id: string,
  body: {
    username?: string
    password?: string
    menu_keys?: string[]
    status?: 'active' | 'disabled'
  },
) {
  return apiPatchJson<PlatformUserRow>(`/api/v1/platform-users/${encodeURIComponent(id)}`, body)
}

export function deletePlatformUser(id: string) {
  return apiDeleteJson<{ ok?: boolean }>(`/api/v1/platform-users/${encodeURIComponent(id)}`)
}
