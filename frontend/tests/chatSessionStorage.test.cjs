const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')
const ts = require('typescript')

const frontendRoot = path.resolve(__dirname, '..')
const storagePath = path.join(frontendRoot, 'src/stores/chatSessionStorage.ts')

function loadStorage() {
  assert.ok(fs.existsSync(storagePath), 'chatSessionStorage.ts must exist')
  const source = fs.readFileSync(storagePath, 'utf8')
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  })
  const loadedModule = { exports: {} }
  new Function('module', 'exports', output.outputText)(
    loadedModule,
    loadedModule.exports,
  )
  return loadedModule.exports
}

function createStorage() {
  const items = new Map()
  return {
    getItem(key) {
      return items.has(key) ? items.get(key) : null
    },
    setItem(key, value) {
      items.set(key, value)
    },
    has(key) {
      return items.has(key)
    },
  }
}

function createSession(id, messages) {
  return {
    id,
    title: id,
    messages,
    createdAt: 1,
    updatedAt: 2,
  }
}

test('userSessionStorageKey scopes chat sessions by user ID', () => {
  const { userSessionStorageKey } = loadStorage()
  assert.equal(userSessionStorageKey('user-1'), 'opsagent_sessions:user-1')
})

test('saveUserSessions writes only under the user-specific key', () => {
  const { saveUserSessions } = loadStorage()
  const storage = createStorage()
  const sessions = [
    createSession('session-1', [{ id: 'u1', role: 'user', content: 'hello', timestamp: 1 }]),
  ]

  saveUserSessions(storage, 'user-1', sessions)

  assert.equal(storage.has('opsagent_sessions:user-1'), true)
  assert.equal(storage.has('opsagent_sessions'), false)
})

test('loadUserSessions returns saved sessions for the matching user only', () => {
  const { loadUserSessions, saveUserSessions } = loadStorage()
  const storage = createStorage()
  const sessions = [
    createSession('session-1', [{ id: 'u1', role: 'user', content: 'hello', timestamp: 1 }]),
  ]

  saveUserSessions(storage, 'user-1', sessions)

  assert.deepEqual(loadUserSessions(storage, 'user-1'), sessions)
  assert.deepEqual(loadUserSessions(storage, 'user-2'), [])
})

test('loadUserSessions returns an empty list for corrupted JSON', () => {
  const { loadUserSessions, userSessionStorageKey } = loadStorage()
  const storage = createStorage()
  storage.setItem(userSessionStorageKey('user-1'), '{not-json')

  assert.deepEqual(loadUserSessions(storage, 'user-1'), [])
})

test('loadUserSessions returns an empty list for non-array JSON', () => {
  const { loadUserSessions, userSessionStorageKey } = loadStorage()
  const storage = createStorage()
  storage.setItem(userSessionStorageKey('user-1'), '{"id":"not-a-session-list"}')

  assert.deepEqual(loadUserSessions(storage, 'user-1'), [])
})

test('saveUserSessions does not persist sessions without any user message', () => {
  const { loadUserSessions, saveUserSessions } = loadStorage()
  const storage = createStorage()
  const sessions = [
    createSession('welcome-only', [{ id: 'welcome', role: 'assistant', content: 'hello', timestamp: 1 }]),
    createSession('empty', []),
    createSession('with-user', [{ id: 'u1', role: 'user', content: 'real question', timestamp: 2 }]),
  ]

  saveUserSessions(storage, 'user-1', sessions)

  assert.deepEqual(loadUserSessions(storage, 'user-1'), [sessions[2]])
})
