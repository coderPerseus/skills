# Log Snippets

Drop-in code for Phase 2 instrumentation. Replace `[DEBUG_X]` with your unique prefix.

## TypeScript / JavaScript

### Basic structured log
```ts
console.log('[DEBUG_X] step-name', JSON.stringify({
  key1: value1,
  key2: value2,
  sentinel: someCondition  // the boolean driving downstream behavior
}, null, 2))
```

### Error log (Error instances need explicit unpacking — `JSON.stringify(err)` returns `"{}"`)
```ts
} catch (e: any) {
  console.error('[DEBUG_X] caught', JSON.stringify({
    message: e?.message,
    stack: e?.stack,
    raw: String(e)
  }, null, 2))
  throw e
}
```

### Global uncaught-error hooks (install once)
```ts
if (!(window as any).__DEBUG_X_HOOKED__) {
  ;(window as any).__DEBUG_X_HOOKED__ = true
  window.addEventListener('unhandledrejection', (e) => {
    const r: any = e.reason
    console.error('[DEBUG_X] unhandledrejection', JSON.stringify({
      message: r?.message, stack: r?.stack, raw: String(r)
    }, null, 2))
  })
  window.addEventListener('error', (e) => {
    console.error('[DEBUG_X] window.error', JSON.stringify({
      message: e.message, errorMessage: e.error?.message, stack: e.error?.stack
    }, null, 2))
  })
}
```

### Granular await breakdown (find which await hangs)
```ts
console.log('[DEBUG_X] stepA start')
const a = await stepA()
console.log('[DEBUG_X] stepA ok', JSON.stringify({ aKeys: Object.keys(a || {}) }, null, 2))

console.log('[DEBUG_X] stepB start')
const b = await stepB(a)
console.log('[DEBUG_X] stepB ok', JSON.stringify({ bLen: b?.length }, null, 2))
```

### React useQuery instrumentation
```ts
const { data, isLoading, error } = useQuery({
  queryKey: ['KEY'],
  queryFn: async () => {
    console.log('[DEBUG_X] queryFn start')
    try {
      const r = await fetcher()
      console.log('[DEBUG_X] queryFn ok', JSON.stringify({
        hasResult: !!r,
        keys: r ? Object.keys(r) : null,
        listLength: r?.list?.length ?? null,
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
  enabled: <condition>
})

useEffect(() => {
  console.log('[DEBUG_X] query state', JSON.stringify({
    enabled: <same condition>,
    isLoading,
    hasError: !!error, errorMessage: (error as any)?.message,
    hasData: !!data,
    listLength: data?.list?.length
  }, null, 2))
}, [isLoading, error, data])
```

### Library internal-structure probe (when `.something` is empty)
```ts
const anyResp = response as any
const memoSummary: Record<string, number> = {}
if (anyResp?.memo instanceof Map) {
  anyResp.memo.forEach((v, k) => {
    memoSummary[k] = Array.isArray(v) ? v.length : -1
  })
}
console.log('[DEBUG_X] response probe', JSON.stringify({
  topKeys: Object.keys(anyResp || {}),
  memoSummary,
  pageContentsType: anyResp?.page_contents?.type,
  shelvesTypes: anyResp?.shelves?.map((s: any) => s?.type)
}, null, 2))
```

## Python

### Basic structured log
```python
import json
print(f"[DEBUG_X] step-name { json.dumps({'k': v, 'sentinel': cond}, indent=2, default=str) }")
```

### Exception log
```python
import traceback
try:
    ...
except Exception as e:
    print(f"[DEBUG_X] caught { json.dumps({'message': str(e), 'stack': traceback.format_exc()}, indent=2) }")
    raise
```

### Global excepthook
```python
import sys, json, traceback
def _hook(exc_type, exc, tb):
    print(f"[DEBUG_X] uncaught { json.dumps({'type': exc_type.__name__, 'message': str(exc), 'stack': ''.join(traceback.format_tb(tb))}, indent=2) }")
sys.excepthook = _hook
```

## Go

### Basic structured log (using stdlib `encoding/json`)
```go
import (
  "encoding/json"
  "fmt"
)

func logJSON(label string, payload map[string]any) {
  b, _ := json.MarshalIndent(payload, "", "  ")
  fmt.Printf("[DEBUG_X] %s %s\n", label, b)
}

// Usage:
logJSON("step-name", map[string]any{
  "key1": value1,
  "sentinel": cond,
})
```

### Recover hook on goroutine
```go
defer func() {
  if r := recover(); r != nil {
    logJSON("panic", map[string]any{
      "value": fmt.Sprint(r),
      "stack": string(debug.Stack()),
    })
    panic(r)
  }
}()
```

## Rust

```rust
use serde_json::json;
eprintln!("[DEBUG_X] step-name {}", serde_json::to_string_pretty(&json!({
    "key1": value1,
    "sentinel": cond,
})).unwrap());
```

## Cleanup grep

After fix is verified, run from project root:

```bash
# Frontend / Node
grep -rE "\[DEBUG_X\]" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.vue" --include="*.svelte" .

# Python
grep -rE "\[DEBUG_X\]" --include="*.py" .

# Go
grep -rE "\[DEBUG_X\]" --include="*.go" .

# Rust
grep -rE "\[DEBUG_X\]" --include="*.rs" .
```

Expected: **0 matches**. If any remain, remove them before declaring done.
