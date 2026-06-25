import type { ChatSession } from '@/types/chat'

interface StorageLike {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

export function userSessionStorageKey(userId: string): string {
  return `opsagent_sessions:${userId}`
}

export function loadUserSessions(storage: StorageLike, userId: string): ChatSession[] {
  try {
    const raw = storage.getItem(userSessionStorageKey(userId))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveUserSessions(storage: StorageLike, userId: string, sessions: ChatSession[]): void {
  const persisted = sessions.filter((session) => session.messages.some((message) => message.role === 'user'))
  try {
    storage.setItem(userSessionStorageKey(userId), JSON.stringify(persisted))
  } catch {
    // Storage can be unavailable or full; chat remains usable in memory.
  }
}
