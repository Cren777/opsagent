const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const test = require('node:test')
const ts = require('typescript')

const frontendRoot = path.resolve(__dirname, '..')
const corePath = path.join(frontendRoot, 'src/composables/questionSuggestionsCore.ts')

function loadCore() {
  assert.ok(fs.existsSync(corePath), 'questionSuggestionsCore.ts must exist')
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

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

test('buildSuggestionCacheKey scopes by user/session and sorts attachment IDs', () => {
  const { buildSuggestionCacheKey } = loadCore()
  const base = {
    userId: 'u1',
    sessionId: 's1',
    datasourceId: 'db1',
    attachmentIds: ['log-b', 'log-a'],
    mode: 'completion',
    draft: '  analyze   this\nlog  ',
    contextId: 'chat-1',
  }

  const sorted = buildSuggestionCacheKey(base)
  assert.equal(sorted, buildSuggestionCacheKey({
    ...base,
    attachmentIds: ['log-a', 'log-b'],
  }))
  assert.notEqual(sorted, buildSuggestionCacheKey({ ...base, userId: 'u2' }))
  assert.notEqual(sorted, buildSuggestionCacheKey({ ...base, sessionId: 's2' }))
  assert.match(sorted, /analyze this log/)
})

test('SuggestionMemoryCache returns defensive copies, expires entries, and evicts oldest entry', async () => {
  const { SuggestionMemoryCache } = loadCore()
  const cache = new SuggestionMemoryCache({ ttlMs: 30, maxEntries: 2 })

  const original = ['first']
  cache.set('a', original)
  original.push('mutated')
  const cached = cache.get('a')
  assert.deepEqual(cached, ['first'])

  cached.push('client mutation')
  assert.deepEqual(cache.get('a'), ['first'])

  cache.set('b', ['second'])
  cache.set('c', ['third'])
  assert.equal(cache.get('a'), undefined)
  assert.deepEqual(cache.get('b'), ['second'])
  assert.deepEqual(cache.get('c'), ['third'])

  await delay(35)
  assert.equal(cache.get('b'), undefined)

  cache.clear()
  assert.equal(cache.get('c'), undefined)
})

test('buildFrontendFallback prioritizes draft, log, datasource, general suggestions and respects limit/dedupe', () => {
  const { buildFrontendFallback } = loadCore()

  assert.deepEqual(
    buildFrontendFallback({
      mode: 'completion',
      draft: '  \u8bf7\u5206\u6790   payment-service   \u9519\u8bef\u65e5\u5fd7\u5e76\u7ed9\u51fa\u975e\u5e38\u8be6\u7ec6\u975e\u5e38\u8be6\u7ec6\u975e\u5e38\u8be6\u7ec6\u975e\u5e38\u8be6\u7ec6\u7684\u6392\u67e5\u6b65\u9aa4  ',
      hasDatasource: true,
      hasLogAttachment: true,
      limit: 4,
    }),
    [
      '\u7ee7\u7eed\u5b8c\u5584\uff1a\u8bf7\u5206\u6790 payment-service \u9519\u8bef\u65e5\u5fd7\u5e76\u7ed9\u51fa\u975e\u5e38\u8be6\u7ec6\u975e\u5e38\u8be6\u7ec6\u975e\u5e38\u8be6\u7ec6\u975e\u5e38\u8be6\u7ec6\u7684...',
      '\u8fd9\u4efd\u65e5\u5fd7\u91cc\u6700\u53ef\u80fd\u7684\u6545\u969c\u539f\u56e0\u662f\u4ec0\u4e48\uff1f',
      '\u8bf7\u6309\u65f6\u95f4\u7ebf\u603b\u7ed3\u65e5\u5fd7\u4e2d\u7684\u5f02\u5e38\u4e8b\u4ef6',
      '\u57fa\u4e8e\u5f53\u524d\u6570\u636e\u6e90\uff0c\u5e2e\u6211\u5206\u6790\u5173\u952e\u6307\u6807\u8d8b\u52bf',
    ],
  )

  assert.deepEqual(
    buildFrontendFallback({
      mode: 'completion',
      draft: 'CPU usage',
      hasDatasource: false,
      hasLogAttachment: true,
      limit: 1,
    }),
    ['\u7ee7\u7eed\u5b8c\u5584\uff1aCPU usage'],
  )

  assert.deepEqual(
    buildFrontendFallback({
      mode: 'context',
      draft: '',
      hasDatasource: true,
      hasLogAttachment: false,
      limit: 3,
    }),
    [
      '\u57fa\u4e8e\u5f53\u524d\u6570\u636e\u6e90\uff0c\u5e2e\u6211\u5206\u6790\u5173\u952e\u6307\u6807\u8d8b\u52bf',
      '\u67e5\u8be2\u6700\u8fd1\u7684\u5f02\u5e38\u6570\u636e\u6709\u54ea\u4e9b\uff1f',
      '\u5f53\u524d\u7cfb\u7edf\u6709\u54ea\u4e9b\u9700\u8981\u5173\u6ce8\u7684\u98ce\u9669\uff1f',
    ],
  )

  assert.deepEqual(
    buildFrontendFallback({
      mode: 'context',
      draft: '',
      hasDatasource: false,
      hasLogAttachment: false,
      limit: 2,
    }),
    [
      '\u5f53\u524d\u7cfb\u7edf\u6709\u54ea\u4e9b\u9700\u8981\u5173\u6ce8\u7684\u98ce\u9669\uff1f',
      '\u5e2e\u6211\u751f\u6210\u4e00\u4efd\u6545\u969c\u6392\u67e5\u6e05\u5355',
    ],
  )
})

test('LatestSuggestionRequest aborts earlier requests, ignores stale completion, and cancel aborts current request', async () => {
  const { LatestSuggestionRequest } = loadCore()
  const latest = new LatestSuggestionRequest()
  let firstResolve
  let firstSignal
  let secondSignal

  const first = latest.run((signal) => {
    firstSignal = signal
    return new Promise((resolve) => {
      firstResolve = resolve
    })
  })

  const second = latest.run(async (signal) => {
    secondSignal = signal
    return 'second'
  })

  assert.equal(firstSignal.aborted, true)
  assert.equal(secondSignal.aborted, false)
  firstResolve('first')
  assert.equal(await first, undefined)
  assert.equal(await second, 'second')

  let cancelSignal
  const cancelled = latest.run((signal) => {
    cancelSignal = signal
    return new Promise((resolve, reject) => {
      signal.addEventListener('abort', () => {
        const error = new Error('aborted')
        error.name = 'AbortError'
        reject(error)
      })
    })
  })

  latest.cancel()
  assert.equal(cancelSignal.aborted, true)
  assert.equal(await cancelled, undefined)

  const nonAbortRejectedAfterCancel = latest.run(() => new Promise((resolve, reject) => {
    setTimeout(() => reject(new Error('late failure')), 0)
  }))
  latest.cancel()
  assert.equal(await nonAbortRejectedAfterCancel, undefined)
})

test('questionSuggestionsCore.ts does not import vue', () => {
  assert.ok(fs.existsSync(corePath), 'questionSuggestionsCore.ts must exist')
  const source = fs.readFileSync(corePath, 'utf8')
  assert.doesNotMatch(source, /from\s+['"]vue['"]/)
  assert.doesNotMatch(source, /require\(['"]vue['"]\)/)
})
