const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')
const ts = require('typescript')

const frontendRoot = path.resolve(__dirname, '..')
const corePath = path.join(frontendRoot, 'src/api/authFetchCore.ts')

function loadCore() {
  assert.ok(fs.existsSync(corePath), 'authFetchCore.ts must exist')
  const source = fs.readFileSync(corePath, 'utf8')
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

function createHarness({ token = 'test-token', status = 200 } = {}) {
  const calls = []
  let cleared = 0
  let redirected = 0
  const { createAuthenticatedFetch } = loadCore()
  const authenticatedFetch = createAuthenticatedFetch({
    request: async (input, init) => {
      calls.push({ input, init })
      return { status }
    },
    getToken: () => token,
    clearToken: () => { cleared += 1 },
    redirectToLogin: () => { redirected += 1 },
  })
  return {
    authenticatedFetch,
    calls,
    getCleared: () => cleared,
    getRedirected: () => redirected,
  }
}

test('adds the current bearer token and preserves existing headers', async () => {
  const harness = createHarness()
  await harness.authenticatedFetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Trace': 'trace-1' },
  })

  const headers = new Headers(harness.calls[0].init.headers)
  assert.equal(headers.get('Authorization'), 'Bearer test-token')
  assert.equal(headers.get('Content-Type'), 'application/json')
  assert.equal(headers.get('X-Trace'), 'trace-1')
})

test('does not send an authorization header when no token exists', async () => {
  const harness = createHarness({ token: null })
  await harness.authenticatedFetch('/api/chat/stream')
  const headers = new Headers(harness.calls[0].init.headers)
  assert.equal(headers.has('Authorization'), false)
})

test('clears and redirects only for an unauthorized response', async () => {
  const unauthorized = createHarness({ status: 401 })
  await unauthorized.authenticatedFetch('/api/chat/stream')
  assert.equal(unauthorized.getCleared(), 1)
  assert.equal(unauthorized.getRedirected(), 1)

  const serverError = createHarness({ status: 500 })
  await serverError.authenticatedFetch('/api/chat/stream')
  assert.equal(serverError.getCleared(), 0)
  assert.equal(serverError.getRedirected(), 0)
})

test('stream chat uses the authenticated fetch adapter', () => {
  const chatSource = fs.readFileSync(
    path.join(frontendRoot, 'src/api/chat.ts'),
    'utf8',
  )
  assert.match(chatSource, /import \{ authFetch \} from '.\/authFetch'/)
  assert.match(chatSource, /return authFetch\('\/api\/chat\/stream'/)
})
