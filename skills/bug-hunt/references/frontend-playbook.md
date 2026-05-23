# Frontend Debug Playbook

Apply the five phases (`SKILL.md`) to browser-rendered frontends — React / Vue / Svelte / vanilla, including web extensions and pages embedding third-party SDKs.

This playbook gives stack-specific tactics; the *what* and *order* still come from `methodology.md`.

## When to pick this playbook

Symptom surfaces in the browser:
- DOM stuck in a state (spinner, empty list, wrong value).
- Console error / unhandled rejection.
- Element renders but interaction broken.
- Visual regression after dependency upgrade.

If the symptom is "HTTP 5xx from API" or "no request fires" the bug may still be backend or network — start frontend, follow the chain.

## Phase 0 in frontend

**Repro essentials**:
- Exact URL (including query string).
- Logged-in user / session state.
- Browser + version (Chrome DevTools and Safari behave differently for some bugs).
- Extension flags / feature flags that may gate the code path.

**Tools to open immediately**:
- DevTools Console (filter by your prefix later).
- DevTools Network (XHR/Fetch tab, "Preserve log").
- React/Vue DevTools (component tree + props/state inspection).

## Phase 1 in frontend: data-flow walk

### React-specific layer table

| Layer | Where to look |
|---|---|
| Render condition | The JSX containing the symptom. Find the boolean / value driving it. |
| Local state | `useState` in the component. |
| Props | Walk to the parent in React DevTools. |
| Context / atom / store | `useContext`, `useAtomValue` (jotai), `useSelector` (Redux), `useStore` (zustand). Search globally for `set<Atom>` to find writers. |
| Hook | Custom hook returning the value; recurse. |
| Server state | `useQuery` (react-query / swr): inspect `data`, `isLoading`, `error`, `status`. |
| Data fetcher | The `queryFn` body. |
| External SDK | If the fetcher calls a third-party lib (youtubei.js, firebase, etc.). |

### React-specific localization tactics

- **React DevTools Profiler**: click the suspect component, see its current `props` / `hooks`. Compare against expected values.
- **Why did this render**: in React DevTools, enable "Highlight updates". Helps when state seems frozen.
- **Stale closures**: a hook reads a variable but doesn't list it in deps. Search the hook body for variables not in the dependency array.
- **Global state writers**: `grep -r "setMyAtom\|setMedianViews" --include="*.{ts,tsx}"` to enumerate.

### Common candidate hypotheses to phrase

- "The query is enabled but never resolves."
- "The query resolves but `data.videos` is empty."
- "The data is correct but the parser drops the K/M suffix."
- "Two parallel callers race and the latter overwrites."

## Phase 2 in frontend: instrumentation patterns

### Standard log line

```ts
console.log('[DEBUG_X] <where>', JSON.stringify({ ...fields }, null, 2))
```

For errors:

```ts
console.error('[DEBUG_X] caught', JSON.stringify({
  message: e?.message, stack: e?.stack, raw: String(e)
}, null, 2))
```

### React-specific instrumentation

**Inside `useQuery` / `useEffect`**:

```ts
const { data, isLoading, error } = useQuery({
  queryFn: async () => {
    console.log('[DEBUG_X] queryFn start', JSON.stringify({ args }, null, 2))
    try {
      const r = await getData()
      console.log('[DEBUG_X] queryFn ok', JSON.stringify({
        keys: r ? Object.keys(r) : null,
        listLength: r?.list?.length,
        firstItem: r?.list?.[0]
      }, null, 2))
      return r
    } catch (e: any) {
      console.error('[DEBUG_X] queryFn threw', JSON.stringify({
        message: e?.message, stack: e?.stack
      }, null, 2))
      throw e
    }
  },
})

useEffect(() => {
  console.log('[DEBUG_X] query state', JSON.stringify({
    isLoading, hasError: !!error, errorMessage: (error as any)?.message,
    hasData: !!data, listLength: data?.list?.length
  }, null, 2))
}, [isLoading, error, data])
```

**Inside a render condition (the sentinel)**:

Add a log right where the symptom-driving condition is evaluated, so you can see the actual driving value:

```ts
const isLoading = medianViews === 0
console.log('[DEBUG_X] render gate', JSON.stringify({
  medianViews, willTriggerLoading: medianViews === 0
}, null, 2))
```

**Inside a custom hook returning a value to many components**: log at the *writer* of the global state, not just the reader, so you see when (and to what) it's being set.

### Black-box SDK / library investigation

When the bug lives behind `lib.someMethod()`:

1. Log each `await` step in the wrapper around the SDK call:

```ts
console.log('[DEBUG_X] svc.init start')
const svc = await Lib.create({ ... })
console.log('[DEBUG_X] svc.init ok')
const res = await svc.doThing(args)
console.log('[DEBUG_X] doThing ok', JSON.stringify({
  resultType: typeof res, keys: Object.keys(res || {}), itemCount: res?.items?.length
}, null, 2))
```

2. If the result is an instance with parsed data, **dump its internal structure**. Many libs expose memos / page contents / raw responses behind getters. Probe with `Object.keys(instance)` and known getters:

```ts
const anyRes = res as any
const memoKeys: string[] = []
const memoSummary: Record<string, number> = {}
if (anyRes?.memo instanceof Map) {
  anyRes.memo.forEach((v, k) => {
    memoKeys.push(k)
    memoSummary[k] = Array.isArray(v) ? v.length : -1
  })
}
console.log('[DEBUG_X] memo dump', JSON.stringify({ memoKeys, memoSummary }, null, 2))
```

This is how you'd discover that 30 `LockupView` nodes exist even though `feed.videos.length === 0`.

3. Check the lib's package version against the official changelog if behavior changed unexpectedly. Stale parsers vs new server payloads is a frequent root cause.

### Cross-origin / iframe / content-script edge cases

Web extensions running in the page context, iframes, or messaging-driven architectures:

- Verify which **realm** your code is running in (`window.location.href` may not be what you expect).
- Verify message passing — log on both sides; correlate with a request-id.
- Beware of `isPlugin()`-style checks that incorrectly classify the realm. If a check returns the unexpected value, that's often the bug.

## Phase 3 in frontend: common multi-layered patterns

| Outer cause | Middle cause | Inner cause |
|---|---|---|
| Lib outdated | New server format | Parser drops field |
| Lib upgraded | API shape changed | Caller still uses old field name |
| New format parsed | Parser categorizes node differently | Getter union excludes new type |
| Getter returns data | Field is UI-string not raw number | Downstream parser drops unit suffix |
| Async race | Two parallel callers | Cache write-after-write overwrites |

When fixing one layer makes the symptom *partially* better (e.g., spinner goes away but value is wrong), there's an inner layer.

## Phase 4 in frontend: surgical fix patterns

- Prefer **narrowest cast** for the bypass: e.g., when the lib's union type misses a node class, use `memo.get('LockupView')` rather than rewriting the lib.
- Prefer **input normalization** over downstream tolerance: if `extractCount` is reused across platforms, expand K/M/B at the *frontend-of-frontend* (the LockupView mapper), not in `extractCount`.
- Keep the type system honest: prefer `as any` in the bypass layer + carefully typed downstream, over silently weakening shared types.

## Phase 5 in frontend: report + cleanup essentials

- The bug report goes in `docs/` (or `<repo>/docs/` if the repo separates).
- Cleanup grep:

```bash
grep -rE "\[DEBUG_X\]" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.vue" --include="*.svelte" .
```

- Optional: add a Sentry tag at the now-instrumented hot spot so future regressions are visible without re-instrumenting.

## Frontend-only hard rules

1. **Never `console.log` to ship.** If a structured log is genuinely useful long-term, route it through your project's logger (with level / sampling), not raw `console.log`.
2. **Don't catch and continue** in render functions. A swallowed error becomes a blank screen with no Sentry breadcrumb.
3. **Beware of "fix" via dependency downgrade.** It papers over a forward-compatibility bug. If you must downgrade, file a follow-up to upgrade properly.

## Worked example

See `references/case-studies/youtube-estimated-quote.md` for a full walkthrough applying every step above.
