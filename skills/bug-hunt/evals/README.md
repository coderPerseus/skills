# bug-hunt evals

Three scenario evals that test whether `bug-hunt` actually enforces its workflow when triggered, instead of being skipped over for ad-hoc debugging.

Each file follows the Anthropic eval schema: `skills`, `query`, optional `files`, and `expected_behavior` (a checklist of behaviors a passing run should exhibit).

There is no built-in runner. To execute:

1. Spin up a fresh Claude Code / API session with the `bug-hunt` skill loaded.
2. Paste the `query` (and attach `files` if any) verbatim.
3. Score the transcript against `expected_behavior` — each item is a pass/fail.

## Scenarios

| File | Stack | Bug shape | What it stress-tests |
|---|---|---|---|
| `01-frontend-stuck-loading.json` | React + jotai | Spinner never disappears | Phase 0 success criterion; Phase 2 unique prefix + sentinel logging |
| `02-backend-silent-500.json` | Node/Express | 500 with empty error response | Phase 2 unhandled-rejection hook; Hard rule #3 (no try/catch bypass) |
| `03-wrong-data-displayed.json` | Any | Number rendered way off | Phase 3 multi-layer cause chain; Phase 5 bug report artifact |

## Scoring

A scenario passes only if **every** `expected_behavior` line is met. Partial credit is meaningless here — the value of the skill is that it enforces the full discipline.

When the skill regresses (e.g. someone slims SKILL.md further and loses a hard rule), at least one of these evals should fail.
