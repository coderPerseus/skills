# Mobile / Desktop App Debug Playbook (stub)

Placeholder. App-specific support is planned for the next iteration.

For now, follow `methodology.md` directly. App-specific tactics that will land here:

## Phase 0 — repro

- Device + OS version, build flavor (debug/release), feature flags.
- Real device vs simulator (some bugs reproduce only on real hardware).
- Network conditions (cellular vs wifi, offline transitions).
- Permissions state (location, camera, push, photos).

## Phase 1 — layer table

| Platform | Layer |
|---|---|
| iOS | View → ViewModel → UseCase → Repo → Network/DB |
| Android | Activity/Fragment/Compose → ViewModel → Domain → Data |
| React Native | JS bundle → bridge → native module |
| Flutter | Widget → State → Repo → Channel |
| Electron | Renderer ↔ IPC ↔ main process |

## Phase 2 — instrumentation

- Sentry crash report + breadcrumbs as primary source.
- Native logs (`adb logcat`, `console.app` for iOS) with prefix filter.
- React Native: `console.log` reaches Metro; for release builds use `__DEV__` guard.
- Electron: separate logs for renderer and main; correlate via IPC channel name.

## Phase 3 — common multi-layered patterns

| Outer | Inner |
|---|---|
| Crash on launch | Old SQLite migration didn't run |
| Blank screen | JS bundle didn't load; native warning eaten |
| Wrong cache | Background fetch updated DB without notifying UI |
| Wrong navigation | Deep link parser fails silently |
| Slow start | Synchronous bridge call on critical path |

## Phase 4 — fix patterns

- Don't ship debug breadcrumbs (Sentry beforeSend hook).
- Migrations: forward-only with explicit version table.
- IPC: use typed schemas, reject unknown messages.

## Phase 5 — cleanup / follow-ups

- Remove ad-hoc logs.
- Add Sentry tag + alert at suspect site.
- Add UI test reproducing the bug.

> Contribution welcome: PR concrete patterns from a real app incident.
