# Debug Methodology — Deep Reference

Companion to `SKILL.md`. Same five phases, expanded with rationale, sub-steps, and decision criteria.

## §0 Reproduce & Frame

### 0.1 Get a deterministic repro

A bug you can't reproduce is a bug you can't verify a fix for. Demand from the user (or recover from logs):

- The exact URL / command / input that triggers the bug.
- Browser / OS / version if relevant.
- Authenticated vs anonymous; which account; which permissions.
- Frequency: 100% / intermittent / specific time of day.

If the user reports an intermittent bug, **try the deterministic case first**; intermittent investigation is a different mode (timing / race / load).

### 0.2 State the success criterion

Phrase it as something you can *verify with a console / API response / screenshot*:

- ❌ "Loading no longer happens"
- ✅ "After page load < 5s, the spinner is gone AND the price div renders a number > 0"

Without a success criterion, you'll declare victory on the first symptomatic improvement (e.g., "spinner gone but value is still wrong" — see Phase 3 case study).

### 0.3 Identify scope early

| Scope question | Why it matters |
|---|---|
| One platform vs all? | Narrows the diff: platform-specific code paths only |
| Old vs new users? | Auth / migration / feature flag |
| Specific route / page? | Routing / SSR vs CSR / lazy-loaded chunk |
| Recently regressed? | Run `git log` against the suspected files |

## §1 Top-down Localization

### 1.1 Start at the symptom

Open the UI / endpoint / log line where the symptom appears. Read the *exact* condition that triggers the bad state.

Example (frontend):

```tsx
// What you SEE:
{isLoading ? <Spinner/> : <Amount value={total} />}

// The condition: isLoading. Where does it come from?
const isLoading = medianViews === 0
```

The bug is now relocated: "why is `medianViews` 0?"

### 1.2 Walk upward, build the layer table

For each value, find the **single writer** (and the readers, but readers don't cause the bug). Document file:line for each layer.

Stop walking up when one of the following:
- You hit a network boundary (API call, library call) — that's where Phase 2 instrumentation will start.
- You hit raw user input — bug is in validation, not data flow.
- You can name a concrete hypothesis (e.g., "library X is returning empty array").

### 1.3 Pitfalls

- **Multiple writers**: if `setState` is called from N places, the bug may be that the *order* is wrong, not the *value*. Note all writers.
- **Stale closures (React)**: a `setX` inside a `useEffect` with missing dependency may write a stale value. Check deps.
- **Global / context state**: jotai atoms, Redux, React Context — these introduce action-at-a-distance writers. Search for `setX` across the repo.

## §2 Full-chain Instrumentation

### 2.1 Picking the prefix

One prefix per investigation. Formats:

- `[DEBUG_<TICKET>]` — ties to issue tracker, e.g., `[DEBUG_PROJ-1234]`
- `[<SCOPE>_DEBUG]` — when no ticket, e.g., `[YUGU_DEBUG]` for "预估报价"

The prefix must be:
- **Unique** (not already in the codebase — grep first).
- **Greppable** (no special regex chars).
- **Removable** with a single command at cleanup time.

### 2.2 Logging payload structure

Use language-native structured logging. Default to JSON-stringify with 2-space indent so the user can paste it back as-is.

**JavaScript/TypeScript:**
```ts
console.log('[DEBUG_X] step name', JSON.stringify({ key: value, ... }, null, 2))
```

**Python:**
```python
import json
print(f"[DEBUG_X] step name {json.dumps({...}, indent=2)}")
```

**Go:**
```go
fmt.Printf("[DEBUG_X] step name %s\n", mustJSON(map[string]any{...}))
```

Include in the payload:
- **Identity**: which call site, which iteration, which item index.
- **Sentinel**: the boolean / decision that drives downstream behavior (`willTriggerLoading: x === 0`).
- **Shape**: `keys: Object.keys(obj)`, `length`, `typeof` — not just values.
- **First sample**: `firstItem: arr[0]` to confirm element shape without dumping everything.

**Errors**: never log raw `Error` — `JSON.stringify(err)` returns `"{}"`. Use `{ message: e.message, stack: e.stack, raw: String(e) }`.

### 2.3 Granular awaits inside black-box async

When `await someLib.doThing()` never resolves, you don't know if `someLib` hung, or if a chained internal `await` hung. Break it open:

```ts
console.log('[DEBUG_X] step A start')
const a = await stepA()
console.log('[DEBUG_X] step A ok')
const b = await stepB(a)
console.log('[DEBUG_X] step B ok')
```

The last log printed identifies the hanging await.

### 2.4 Global error / rejection hooks

Some bugs throw silently (uncaught promise rejection swallowed by a framework). Install at the top of your instrumented function:

```ts
if (!window.__DEBUG_HOOKED__) {
  window.__DEBUG_HOOKED__ = true
  window.addEventListener('unhandledrejection', (e) => {
    const r: any = e.reason
    console.error('[DEBUG_X] unhandledrejection', JSON.stringify({
      message: r?.message, stack: r?.stack, raw: String(r)
    }, null, 2))
  })
  window.addEventListener('error', (e) => {
    console.error('[DEBUG_X] window.error', JSON.stringify({
      message: e.message, stack: e.error?.stack
    }, null, 2))
  })
}
```

Backend equivalents: `process.on('unhandledRejection')`, Python `sys.excepthook`, Go `defer recover()`.

### 2.5 Ask the user to repro

Once logs are in place, give the user a clear ask:

> "Reproduce the bug, copy lines matching `[DEBUG_X]` from the console (or run `grep '[DEBUG_X]' app.log`), and paste them back here."

Do **not** continue making code changes until you have the output. Logs from one round inform the next round's hypothesis.

## §3 Layered Root Cause Analysis

### 3.1 The cause chain pattern

A symptom may have a single proximate cause, but high-quality investigations frequently surface 2-3 chained causes. Pattern:

```
Symptom: <observable>
  Proximate cause: <closest reason>
    Underlying cause: <reason for the proximate cause>
      Root cause: <reason for the underlying cause>
```

Indicators you're not at the root yet:

- "Why is this happening?" still has a meaningful answer.
- The fix would prevent this exact bug but a 1-character change elsewhere would re-introduce it.
- Other engineers would be surprised by the failure mode.

### 3.2 Verifying each layer

For each link in the chain, you must have evidence:

| Link | Evidence type |
|---|---|
| "Library returns empty array" | Phase 2 log showing `length: 0` |
| "Library doesn't parse new format" | memo / raw response dump showing real structure exists |
| "Field name changed" | type definition / official changelog / source |

**Don't accept "probably" as evidence.** Confirm via grep, type inspection, or a one-off test call.

### 3.3 Partial fixes

It's common to fix the proximate cause and discover the bug isn't fully gone. **Don't celebrate prematurely**. The success criterion from Phase 0 is your only gate.

Worked example (see case study):

1. Upgraded library — `getVideos.length` still 0 → not done.
2. Bypassed library getter via memo — got 30 videos but `medianViews: 30` (way too low) → not done.
3. Expanded K/M/B units — `medianViews: 27500` ✅ matches expected magnitude → done.

## §4 Surgical Fix & Verify

### 4.1 Minimum diff principle

- Change the smallest set of lines that fixes the proven cause.
- Do not refactor unrelated code.
- Do not "improve" naming or types you don't have to touch.
- Do not delete dead code in the same commit.

Justification: every additional change increases review surface and regression risk. The investigation's value is **the fix is provably tied to the cause**.

### 4.2 What's NOT a fix

- `value || 0` masking `undefined` — moves bug downstream.
- `try { ... } catch {}` — hides the next bug.
- `setTimeout(check, 100)` — race condition you didn't solve.
- `// HACK: ...` — declares defeat in code.

If you're writing one of these, return to Phase 1.

### 4.3 Verification protocol

Re-run the repro **with Phase 2 logs still present**:

1. Confirm each previously-broken log line now reports the expected value.
2. Confirm sentinel boolean flips (`willTriggerLoading: true → false`).
3. Confirm an *unaffected* path still works (e.g., the other platforms).
4. Capture the verification logs — they go into the bug report.

### 4.4 Scope creep guard

While in the file you fixed, you'll see other code that *could* be improved. **Don't touch it now.** Note it for a separate PR. Mixing improvements into a fix:
- Lengthens review.
- Confuses git-blame for future bugs.
- Risks introducing a new bug correlated with the "fix".

## §5 Report + Cleanup

### 5.1 The report

Use `templates/bug-report.md`. Sections:

1. **Metadata**: date, scope, severity.
2. **Symptom**: what the user saw, with screenshots / log excerpts.
3. **Root cause**: the chain (use the indent style from §3.1).
4. **Investigation**: how you got there — phase 1 layer table + key phase 2 logs.
5. **Fix**: code diff + rationale per change.
6. **Verification**: before/after table.
7. **Files touched**.
8. **Follow-ups**: monitoring, dependency hygiene, test coverage gaps.

Save under `docs/` (or project equivalent) with name `bugfix-<short-slug>.md`. Use today's date in metadata.

### 5.2 Log cleanup

```bash
grep -r "\[DEBUG_X\]" . --include="*.ts" --include="*.tsx" --include="*.py" --include="*.go"
```

Expected output: **0 hits**. If anything matches, remove it. Run the type-checker after cleanup.

### 5.3 Follow-up suggestions

Common patterns:

- **Dependency hygiene** when a library version mismatch caused the bug → propose a quarterly dependency-review cadence.
- **Telemetry** when a silent failure caused the bug → add a Sentry breadcrumb / structured log at the point that returned the bad value.
- **Regression test** when the bug was data-shape-related → add a test fixture that captures the new shape.
- **Documentation** when the bug came from an undocumented behavior → file a docs PR upstream or note it in your team's CLAUDE.md / AGENTS.md.

Don't *implement* the follow-ups during the fix (scope creep). List them in the report so the user can decide.
