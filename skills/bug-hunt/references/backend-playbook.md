# Backend Debug Playbook (stub)

This file is a placeholder. Backend support is planned for the next iteration.

For now, follow `methodology.md` directly. Backend-specific tactics that will land here:

## Phase 0 — repro tactics

- Capture request: method, path, headers, body, auth, downstream service versions.
- Identify whether the bug is in a single request, batch, or schedule.

## Phase 1 — layer table for backend

| Layer | What to inspect |
|---|---|
| HTTP entry | route handler / controller |
| Validation | request schema parser |
| Business logic | service / use-case |
| Data access | repository / ORM / raw SQL |
| External call | downstream API client |
| Database | query, EXPLAIN plan, indexes |
| Cache | Redis / in-memory |

## Phase 2 — instrumentation patterns

- Request-id correlation ID through every log line.
- Structured logger (zap / pino / structlog) with consistent fields.
- DB EXPLAIN logged at suspect query sites.
- `tcpdump` / mitmproxy when third-party API is suspect.
- For hanging requests: stack dumps (Go `SIGQUIT`, Python `py-spy`, Node `--inspect`).

## Phase 3 — common multi-layered patterns

| Outer | Inner |
|---|---|
| Slow API | Missing index |
| Wrong data | Cache invalidation skipped |
| 500 error | Type mismatch from upstream change |
| Race condition | Two writers without lock |
| OOM | N+1 query loading too many objects |

## Phase 4 — fix patterns

- Index changes: review `EXPLAIN` before and after.
- Cache invalidation: think about read-your-own-writes.
- Schema changes: forward + backward compatible migrations.

## Phase 5 — cleanup / follow-ups

- Remove ad-hoc logs (same grep rule as frontend).
- Suggest dashboards / alerts at the now-instrumented hot spot.
- Add regression test exercising the bug's input.

> Contribution welcome: PR concrete patterns from a real backend incident.
