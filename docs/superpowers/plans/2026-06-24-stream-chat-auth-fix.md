# Stream Chat Authentication Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Ensure authenticated streaming chat requests carry the current Bearer token and expire the browser session consistently on HTTP 401.

**Architecture:** Add a small dependency-injected authenticated fetch core that can be tested with Node's built-in test runner, then wire it to browser token storage in a thin adapter. The existing SSE parser remains unchanged and only switches from raw `fetch` to the authenticated wrapper.

**Tech Stack:** Vue 3, TypeScript, native Fetch API, Node built-in test runner, Vite, pytest

---

### Task 1: Add Failing Authenticated Fetch Tests

**Files:**
- Create: `frontend/tests/authFetch.test.cjs`
- Modify: `frontend/package.json`
- Test: `frontend/tests/authFetch.test.cjs`

- [x] **Step 1: Add the Node test script**

Add this script to `frontend/package.json`:

```json
"test:auth-fetch": "node --test tests/authFetch.test.cjs"
```

- [x] **Step 2: Write the failing behavior tests**

Create `frontend/tests/authFetch.test.cjs`:

```javascript
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
```

- [x] **Step 3: Run the tests and verify red**

Run:

```bash
cd frontend
npm run test:auth-fetch
```

Expected: FAIL because `authFetchCore.ts` does not exist and `chat.ts` still uses raw `fetch`.

### Task 2: Implement Authenticated Fetch and Integrate Streaming Chat

**Files:**
- Create: `frontend/src/api/authFetchCore.ts`
- Create: `frontend/src/api/authFetch.ts`
- Modify: `frontend/src/api/chat.ts`
- Test: `frontend/tests/authFetch.test.cjs`

- [x] **Step 1: Implement the testable fetch core**

Create `frontend/src/api/authFetchCore.ts`:

```typescript
export interface AuthenticatedFetchDependencies {
  request: typeof fetch
  getToken: () => string | null
  clearToken: () => void
  redirectToLogin: () => void
}

export function createAuthenticatedFetch({
  request,
  getToken,
  clearToken,
  redirectToLogin,
}: AuthenticatedFetchDependencies): typeof fetch {
  return async (input, init = {}) => {
    const headers = new Headers(init.headers)
    const token = getToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    const response = await request(input, { ...init, headers })
    if (response.status === 401) {
      clearToken()
      redirectToLogin()
    }
    return response
  }
}
```

- [x] **Step 2: Wire the browser adapter**

Create `frontend/src/api/authFetch.ts`:

```typescript
import { clearStoredToken, getStoredToken } from './authToken'
import { createAuthenticatedFetch } from './authFetchCore'

export const authFetch = createAuthenticatedFetch({
  request: window.fetch.bind(window),
  getToken: getStoredToken,
  clearToken: clearStoredToken,
  redirectToLogin: () => {
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  },
})
```

- [x] **Step 3: Use the adapter in stream chat**

At the top of `frontend/src/api/chat.ts` add:

```typescript
import { authFetch } from './authFetch'
```

Replace:

```typescript
return fetch('/api/chat/stream', {
```

with:

```typescript
return authFetch('/api/chat/stream', {
```

Do not change SSE parsing or callbacks.

- [x] **Step 4: Run the focused tests and verify green**

Run:

```bash
cd frontend
npm run test:auth-fetch
```

Expected: 4 tests pass.

- [x] **Step 5: Run TypeScript validation**

Run:

```bash
cd frontend
npx vue-tsc -p tsconfig.app.json --noEmit
```

Expected: exit 0.

### Task 3: Rebuild Deployment Assets

**Files:**
- Modify: `ops_agent/api/static/dist/index.html`
- Replace hashed files under: `ops_agent/api/static/dist/assets/`

- [x] **Step 1: Build the frontend with the supported Node runtime**

Run:

```bash
cd frontend
npm run build
```

Expected: Vite exits 0 and writes to `ops_agent/api/static/dist/`.

- [x] **Step 2: Verify the built bundle contains authenticated stream chat**

Run the encoding and build contract test:

```bash
python -m pytest tests/test_source_encoding.py -q
```

Expected: 4 tests pass.

### Task 4: Full Regression Verification

**Files:**
- Verify only; no planned source edits.

- [x] **Step 1: Run authentication and API contract tests**

Run:

```bash
conda run -n chatchat python -m pytest tests/test_api_main_contract.py tests/test_auth_routes.py tests/test_auth_service.py tests/test_source_encoding.py -q
```

Expected: all tests pass.

- [x] **Step 2: Compile Python sources**

Run:

```bash
python -m compileall -q ops_agent config scripts tests
```

Expected: exit 0.

- [x] **Step 3: Check generated asset references**

Parse `ops_agent/api/static/dist/index.html` and verify every `/assets/*` reference exists beneath the dist directory.

Expected: no missing assets.

- [x] **Step 4: Inspect the final diff**

Run:

```bash
git diff --check
git status -sb
```

Expected: no whitespace errors; prior uncommitted work remains intact; this fix adds only the authenticated fetch files, chat integration, test, package script, plan, and regenerated assets.
