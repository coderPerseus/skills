---
name: bug-hunt
description: Systematic root-cause debugging for software bugs (frontend, backend, mobile). Use when the user reports a symptom that needs investigation — "卡死 / loading / 报错 / 数据不对 / 行为异常 / 复现了 bug / 帮我查一下为什么 X 不工作 / 排查一下 / debug this / why is X broken / hunt the bug / investigate". Walks through five phases — reproduce → top-down localize → full-chain instrumentation → layered root cause → surgical fix + bug report. Distinct from generic `hunt` / `investigate` by enforcing multi-layered cause chains, structured log discipline (unique prefix + JSON.stringify), and a required bug-report artifact in `docs/`. Anti-patterns: do NOT guess a fix without evidence, do NOT bypass with try/catch, do NOT delete unfamiliar state.
---

# bug-hunt — Methodology-driven Root-Cause Investigation

This skill encodes a reusable, evidence-driven debugging workflow. It exists to prevent two anti-patterns:

1. **Pattern-match a fix from the symptom** (e.g., "loading? add error handling") without proving the root cause.
2. **Bypass instead of fix** (e.g., swallow exceptions, add fallbacks, set defaults) to make the symptom go away.

The workflow itself is **language-, framework- and domain-agnostic**. Subdomain playbooks (`references/frontend-playbook.md`, etc.) describe how to apply each phase in a specific tech stack.

## When to use

Invoke this skill when the user says any of:

- "debug this" / "fix this bug" / "投查一下" / "排查一下"
- "why is X not working" / "X 一直 loading" / "X 不对"
- "find the root cause"
- Reports an unexpected error / crash / stuck state / wrong value
- Asks for a bug report after fixing

Do **not** invoke for: new feature design, refactors without a failing scenario, performance tuning (use a benchmark skill), code review.

## The five phases

Follow these phases **in order**. Do not jump phases. If a later phase produces evidence contradicting an earlier conclusion, return to the earlier phase.

### Phase 0 — Reproduce & Frame
- Get a reliable repro path (URL, command, input).
- Define the success criterion in measurable terms (e.g., "spinner disappears AND amount > 0").
- Identify scope: does it affect all users / one platform / one route?
- If you cannot reproduce, STOP and ask the user for repro steps or logs.

### Phase 1 — Top-down Localization
Walk from the user-visible symptom upward through the data flow. Build a layer table:

| Layer | File:line | Decision / value |
|---|---|---|
| UI render | `Component.tsx:42` | `isLoading = value === 0` |
| Prop source | `Parent.tsx:111` | `value` from atom / context / state |
| Writer | `Hook.ts:55` | who calls `setValue` |
| Input | `service.ts:88` | upstream API / library call |

End the phase with **named candidate hypotheses** — not "something's wrong upstream" but "`getYoutubeData` returns empty videos" or "`extractCount` mis-parses K suffix".

### Phase 2 — Full-chain Instrumentation
Add structured logs at every layer in the table.

**Rules**:
- Use a **unique prefix** like `[DEBUG_<TICKET>]` so the user can grep cleanly. Single prefix across the whole investigation.
- Wrap every payload with `JSON.stringify(obj, null, 2)` (or language equivalent) so it copy-pastes intact, not as a DevTools live object.
- Include **sentinel fields** that summarize the decision logic (e.g., `willTriggerLoading: medianViews === 0`).
- For black-box async chains, insert a log **before and after each `await`** to find which step hangs.
- For unhandled-rejection categories, install global hooks so silent throws surface.

Ask the user to reproduce, copy console output, and paste it back. **Do not synthesize fake logs in your head**.

Detailed templates: see `references/methodology.md` §2 and `templates/log-snippets.md`.

### Phase 3 — Layered Root Cause Analysis
Bugs are often **multi-layered**. Don't stop at the first cause found.

Pattern: each time you fix one layer and the symptom *partially* improves, ask "what's the next layer?". Maintain a cause chain:

```
Outer cause
  └─ when fixed, exposes:  Middle cause
      └─ when fixed, exposes:  Inner cause
```

A real example (see `references/case-studies/youtube-estimated-quote.md`):

```
YouTube changed lockupViewModel
  └─ outdated library doesn't parse it → videos = []
      └─ upgraded library, but Feed.videos union excludes LockupView → videos still = []
          └─ memo-extracted LockupView gives "4.6K views" UI string
              └─ extractCount drops K → median = 30 (way off)
```

Each level required a separate fix. Stop only when the success criterion is met.

### Phase 4 — Surgical Fix & Verify
- Smallest possible change. Don't refactor neighboring code.
- Don't add error handling, retries, or fallbacks unless the test case requires them — see karpathy-guidelines.
- Keep the Phase 2 logs in place during verification. Confirm:
  - Each previously-zero/empty value now has the expected non-zero/non-empty value.
  - Sentinel field flips (`willTriggerLoading: true → false`).
  - No collateral damage in other paths (e.g., other platforms still work).

### Phase 5 — Report + Cleanup
- Use `templates/bug-report.md` as the report skeleton. Fill in: symptom, root cause (multi-layered if applicable), investigation steps with evidence, fix, verification table, follow-up suggestions.
- Save the report to `docs/` (or the project's docs folder) with a kebab-case filename.
- **Remove the debug logs**: a single `grep -r "<your-prefix>"` should return zero hits.
- Suggest monitoring (Sentry, structured logs, dashboards) so the next regression of this kind is caught automatically.

## Subdomain playbooks

Depending on the stack, follow one of:

- **Frontend** (browser, React/Vue/Svelte, web extensions, third-party SDKs): see `references/frontend-playbook.md`
- **Backend** (HTTP servers, DB, queues): see `references/backend-playbook.md` (stub — TBD)
- **Mobile / Desktop app** (iOS/Android/Electron): see `references/app-playbook.md` (stub — TBD)

If unsure which playbook applies, ask the user, or pick by where the symptom surfaces (UI → frontend; 500 response → backend; crash report → app).

## Hard rules

These rules override convenience:

1. **No fix without evidence.** Every code change must be traceable to a log/output that proves the bug exists at that location.
2. **One unique log prefix per investigation.** Reuse it everywhere; clean it all up at the end.
3. **Never bypass.** A `try/catch` that swallows the error, a `||` fallback that masks `undefined`, or a `// FIXME` left behind is not a fix.
4. **Always write the bug report.** The investigation is not done until the markdown report lands in `docs/`.
5. **Cleanup is a phase, not optional.** Logs that ship to prod are bugs.

## Anti-patterns to refuse

- "Just add a retry" — without knowing why it fails.
- "Set a sensible default" — when 0 is itself the symptom.
- "Bump the timeout" — when the call never resolves.
- "Wrap in try/catch and log" — and then return early as if nothing happened.

When tempted, **return to Phase 1** and find the real source.

## Output expectations

Each phase ends with a concrete artifact:

| Phase | Artifact |
|---|---|
| 0 | A one-line repro and success criterion |
| 1 | A layer table with file:line entries |
| 2 | A diff adding logs + an explicit ask for user to paste output |
| 3 | A cause chain (text, may be multi-level) |
| 4 | A code diff + verification log entries |
| 5 | `docs/bugfix-<slug>.md` saved + zero prefix grep hits |

## Further reading

- `references/methodology.md` — Deep dive on each phase, with templates.
- `references/frontend-playbook.md` — Frontend-specific instrumentation patterns.
- `references/case-studies/youtube-estimated-quote.md` — Worked example walking through all five phases.
- `templates/bug-report.md` — Bug report skeleton.
- `templates/log-snippets.md` — Logging templates per language/framework.
