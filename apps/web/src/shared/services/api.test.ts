/**
 * TB-14：前端 RBAC 与请求头契约（角色来自 localStorage）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

let mem: Record<string, string> = {}

vi.stubGlobal(
  'localStorage',
  {
    getItem: (k: string) => (k in mem ? mem[k] : null),
    setItem: (k: string, v: string) => {
      mem[k] = v
    },
    removeItem: (k: string) => {
      delete mem[k]
    },
    clear: () => {
      mem = {}
    },
  } as Storage,
)

describe('getStoredRole', () => {
  beforeEach(() => {
    mem = {}
  })

  it('defaults to readonly when no role stored', async () => {
    const { getStoredRole } = await import('./api')
    expect(getStoredRole()).toBe('readonly')
  })

  it('returns admin when set', async () => {
    mem['rsa_user_role'] = 'admin'
    const { getStoredRole } = await import('./api')
    expect(getStoredRole()).toBe('admin')
  })

  it('returns operator when set', async () => {
    mem['rsa_user_role'] = 'operator'
    const { getStoredRole } = await import('./api')
    expect(getStoredRole()).toBe('operator')
  })

  it('ignores invalid values', async () => {
    mem['rsa_user_role'] = 'hacker'
    const { getStoredRole } = await import('./api')
    expect(getStoredRole()).toBe('readonly')
  })
})
