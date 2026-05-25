---
name: bug-hunt
description: 'Systematic root-cause debugging for software bugs (frontend, backend, mobile). Use when the user reports a symptom that needs investigation — "卡死 / loading / 报错 / 数据不对 / 行为异常 / 复现了 bug / 帮我查一下为什么 X 不工作 / 排查一下 / debug this / why is X broken / hunt the bug / investigate". Walks through five phases — reproduce → top-down localize → full-chain instrumentation → layered root cause → surgical fix + bug report. Enforces multi-layered cause chains, structured log discipline (unique prefix + JSON.stringify), and a required bug-report artifact.'
---

# bug-hunt — Methodology-driven Root-Cause Investigation

Evidence-driven debugging workflow. Walks every bug through five phases — never skip ahead. The deep prose lives in [references/methodology.md](references/methodology.md); this file is the contract.

## When to use

Invoke when the user says any of:

- "debug this" / "fix this bug" / "排查一下" / "投查一下"
- "why is X not working" / "X 一直 loading" / "X 不对"
- "find the root cause"
- Reports an unexpected error / crash / stuck state / wrong value
- Asks for a bug report after fixing

Do **not** invoke for: new feature design, refactors without a failing scenario, performance tuning (use a benchmark skill), code review.

## Five phases — table of contents

Follow in order. If later evidence contradicts earlier conclusions, return to the earlier phase.

| Phase | Goal | Deep reference |
|---|---|---|
| 0 — Reproduce & Frame | Deterministic repro + measurable success criterion | [methodology.md §0](references/methodology.md) |
| 1 — Top-down Localization | Layer table (file:line per row), end with named hypotheses | [methodology.md §1](references/methodology.md) |
| 2 — Full-chain Instrumentation | Structured logs with one unique prefix at every layer | [methodology.md §2](references/methodology.md) · [templates/log-snippets.md](templates/log-snippets.md) |
| 3 — Layered Root Cause Analysis | Cause chain, multi-layer when applicable | [methodology.md §3](references/methodology.md) |
| 4 — Surgical Fix & Verify | Smallest diff; verify with the Phase 2 logs still in place | [methodology.md §4](references/methodology.md) |
| 5 — Report + Cleanup | `docs/` artifact + zero-prefix grep | [methodology.md §5](references/methodology.md) · [templates/bug-report.md](templates/bug-report.md) |

**Subdomain playbooks** (apply each phase in a specific stack):

- Frontend — browser, React/Vue/Svelte, web extensions, third-party SDKs: [references/frontend-playbook.md](references/frontend-playbook.md)
- Backend — HTTP servers, DB, queues: [references/backend-playbook.md](references/backend-playbook.md)
- Mobile / Desktop — iOS/Android/Electron: [references/app-playbook.md](references/app-playbook.md)

**Worked example** (all five phases end-to-end): [references/case-studies/youtube-estimated-quote.md](references/case-studies/youtube-estimated-quote.md)

If unsure which playbook applies, pick by where the symptom surfaces (UI → frontend; 500 response → backend; crash report → app).

## Hard rules

Non-negotiable. They override convenience.

1. **No fix without evidence.** Every code change must be traceable to a log/output that proves the bug exists at that location.
2. **One unique log prefix per investigation.** Reuse it everywhere; clean it all up at the end.
3. **Never bypass.** A `try/catch` that swallows the error, a `||` fallback that masks `undefined`, a `// FIXME` left behind — none are fixes. When tempted, return to Phase 1.
4. **Always write the bug report.** The investigation is not done until the markdown report lands in `docs/`.
5. **Cleanup is a phase, not optional.** Logs that ship to prod are bugs.
6. **Official docs + GitHub issues first, low-quality never.** External lookups have a strict priority order:
   1. **Official documentation / source / changelog** of the library or platform (e.g., `react.dev`, `nodejs.org/api`, `developer.mozilla.org`, the package's own GitHub source & release notes, RFC / W3C specs, official type definitions).
   2. **GitHub issues & discussions on the maintainer's own repo** — especially closed issues linked to a commit/PR.
   3. Fallback: vendor engineering blogs, Stack Overflow answers authored or cited by maintainers, well-known long-form engineering blogs.

   **Banned — never cite, never paste conclusions from:** CSDN, 博客园 低质量镜像, 百度知道 / 百度经验, 360doc, content-farm 聚合站, AI-generated SEO articles, undated translation mirrors. Their root-cause analyses are routinely wrong and will send you toward a fake fix.

   Every external URL you relied on must appear in the bug report so the evidence chain is auditable. See [methodology.md §3.4](references/methodology.md) for the full hierarchy and rationale.

## Per-phase artifact — definition of done

Each phase ends with a concrete output. If a phase ends without its artifact, you skipped a step.

| Phase | Required artifact |
|---|---|
| 0 | One-line repro + measurable success criterion |
| 1 | Layer table with file:line entries + named hypotheses |
| 2 | Diff adding logs + explicit ask for user to paste console output |
| 3 | Cause chain (text, may be multi-level) |
| 4 | Code diff + verification log entries showing sentinel flip |
| 5 | `docs/bugfix-<slug>.md` saved + zero prefix grep hits |
