# Case Study — YouTube 预估报价卡片永久 Loading

Worked example of the full five-phase debug methodology, drawn from a real session (May 2026).

This is a teaching artifact, not a project doc. It exists so future debugging sessions can see the methodology applied end-to-end on a concrete bug.

## The bug, in one sentence

YouTube KOL 信息卡里的"预估报价"区域永久显示 loading spinner;同样代码在 TikTok / Instagram 上正常。

## Phase 0 — Reproduce & Frame

**Repro**: open any YouTube channel URL (e.g., `https://www.youtube.com/@DrTraceyMarks`) with the browser extension loaded. Wait for the info card to render. The "预估报价" sub-card shows a spinner that never resolves.

**Success criterion**:
1. Spinner disappears within 5s of page load.
2. The "$<number>" amount renders.
3. The amount magnitude matches expectation (e.g., a creator with 27.5K median views should show a four-digit USD estimate, not "30").

**Scope**: YouTube only. TikTok / Instagram / Twitter unaffected.

## Phase 1 — Top-down Localization

Walked the data flow from the spinner upward:

| Layer | File:line | Decision / value |
|---|---|---|
| Render | `components/YuGuBaoJia.tsx:42` | `isMedianViewsLoading = medianViews === 0` controls spinner |
| Prop | `components/AudienceCard.tsx:164,285` | `medianViews` from atom `medianViewsState` |
| Default | `store/index.ts:16` | `atom<number>(22000)` — default isn't 0 |
| Writer | `components/KOLStatistics.tsx:126-162` | only place calling `setMedianViews` |
| Calc | `utils/youtube/getLatestVideosViewCountStatistics.ts:103` | `getYoutubeStatistics(videos, ...)` |
| Prop in | `components/InfoCard.tsx:661` | `videos = platformData.youtube?.videos` |
| Hook | `hooks/useKOLInfo.ts:94` | `useQuery({ queryFn: () => getYoutubeData(...) })` |
| Fetcher | `utils/youtube/index.ts:371` | calls `youtubei.js` lib |

**Named hypotheses at end of Phase 1**:
- H1: `youtubeData.videos` is empty/undefined.
- H2: `videos` array is populated but `extractCount(item.views)` returns 0.
- H3: Query never resolves (stuck loading).

## Phase 2 — Full-chain Instrumentation

Picked prefix `[YUGU_DEBUG]` (unique — grep confirmed 0 hits before adding).

Added structured logs (all using `JSON.stringify(obj, null, 2)`):

1. **In `KOLStatistics.tsx`** — log the writer:
   ```ts
   console.log('[YUGU_DEBUG][KOLStatistics] setMedianViews',
     JSON.stringify({ medianViews, willTriggerLoading: medianViews === 0 }, null, 2))
   ```

2. **In `useKOLInfo.ts`** — log the query lifecycle:
   ```ts
   useEffect(() => {
     console.log('[YUGU_DEBUG][useKOLInfo] youtube query state', JSON.stringify({
       isYoutubeDataLoading, hasError: !!youtubeDataError,
       hasYoutubeData: !!youtubeData, videosLength: youtubeData?.videos?.length
     }, null, 2))
   }, [...])
   ```

3. **In `getYoutubeData()`** — log each `await` step:
   ```ts
   console.log('[YUGU_DEBUG][getYoutubeData] called', JSON.stringify({ url, isPlugin: isPlugin() }, null, 2))
   const svc = await getYoutubeService()
   console.log('[YUGU_DEBUG][getYoutubeData] svc ok')
   const navEnd = await svc.resolveURL(url)
   console.log('[YUGU_DEBUG][getYoutubeData] resolveURL ok', ...)
   // ... etc, before/after every await
   ```

4. **In `getYoutubeStatistics()`** — log raw inputs + computed output:
   ```ts
   console.log('[YUGU_DEBUG][getYoutubeStatistics] inputs',
     JSON.stringify({ totalVideoCount: videos.length, viewSamples }, null, 2))
   ```

Asked the user to repro and paste console output filtered by `YUGU_DEBUG`.

## Phase 3 — Layered Root Cause (this is where the bug got interesting)

Three rounds of logs revealed a four-layer cause chain:

### Round 1 — H1 confirmed but deeper

Logs showed:
- `youtube query state: { isLoading: true, hasError: false }` — query stuck pending.
- `getYoutubeData called` printed, but no later steps.

Granular `await` logs added → bug visible:
- `svc ok / resolveURL ok / getChannel ok / getAbout ok / getVideos ok` all printed.
- But `getVideos ok: { count: 0 }`.

So: query *did* resolve. videos were *zero*. Why?

### Round 2 — Library doesn't parse YouTube's new shape

Added a deep memo dump:

```ts
const memo: Map<string, any[]> = anyResp?.memo
memo.forEach((arr, key) => { memoSummary[key] = arr.length })
```

Result: `LockupView: 30`, `LockupMetadataView: 30`, `RichItem: 30`.

So 30 videos *are* in the response, but classified as `LockupView` — a new YouTube container type. `youtubei.js@10.3.0` (the installed version) doesn't recognize `LockupView` in its `Feed.videos` getter union.

**Layer 1 root cause identified**: library version chain — YouTube migrated to `lockupViewModel`; the parser version we used dropped them.

Fix attempt: upgraded `youtubei.js: ^10.3.0 → ^17.0.1`.

Repro again. `getVideos: { count: 0 }`. Still zero.

### Round 3 — Newer library parses but getter union still excludes LockupView

Inspected `node_modules/youtubei.js@17.0.1/.../Feed.d.ts`:

```ts
get videos(): ObservedArray<CompactVideo | GridVideo | PlaylistPanelVideo
  | PlaylistVideo | ReelItem | ShortsLockupView | Video | WatchCardCompactVideo>
```

**`LockupView` is missing from the union** even in v17. The parser categorizes the nodes correctly into memo, but `.videos` filters by these specific types only.

**Layer 2 root cause**: library getter union is incomplete for the new node type.

Fix: bypass `.videos` by reading `memo.get('LockupView')` directly, filter `content_type === 'VIDEO'`, map to our domain shape.

After this fix: `videos.length: 30` ✅. But `medianViews: 30` ❌ (expected ~27000).

### Round 4 — Downstream parser drops unit suffix

LockupView's view count text is the UI string, e.g., `"4.6K views"`.

The downstream `extractCount`:

```ts
const cleanedStr = str.replace(/[^0-9]/g, '')
return parseInt(cleanedStr, 10) || 0
```

Strips non-digits: `"4.6K views"` → `"46"` → 46. The `K` (1000×) and `.` are eaten.

**Layer 3 root cause**: the value-extraction utility silently drops magnitude suffixes; only worked historically because `Video.view_count.text` returned full digits like `"157,497 views"`.

Fix: in the LockupView mapping step, expand K/M/B in place to full integers before handing off:

```ts
const expandCountSuffix = (t: string) => {
  const m = t.match(/([\d.,]+)\s*([KkMmBb])\b/)
  if (!m) return t
  const num = parseFloat(m[1].replace(/,/g, ''))
  const mult = { K: 1e3, M: 1e6, B: 1e9 }[m[2].toUpperCase()]
  return t.replace(m[0], String(Math.round(num * mult)))
}
// "4.6K views" → "4600 views"
```

`extractCount` left unchanged — other platforms unaffected.

### Final cause chain

```
YouTube migrated to lockupViewModel
  └─ youtubei.js@10.3.0 doesn't parse it → videos: []
      └─ upgraded to v17, but Feed.videos union missing LockupView → videos still []
          └─ memo-extracted LockupView gives "4.6K views" UI string
              └─ extractCount strips K → median underflows by 1000×
                  → medianViews: 30 → spinner gone but amount nonsense
```

## Phase 4 — Surgical Fix & Verify

Three changes, all in two files:

1. `package.json` — `youtubei.js: ^10.3.0 → ^17.0.1`.
2. `utils/youtube/index.ts` — make `videos.map` defensive across `Video / GridVideo / LockupView` shapes; when `feed.videos.length === 0`, fall back to `memo.get('LockupView')`.
3. `utils/youtube/index.ts` — `expandCountSuffix()` applied to the views text before downstream `extractCount` sees it.

`extractCount` itself **not touched** — preserved TikTok / Instagram paths.

**Verification** (with all `[YUGU_DEBUG]` logs still in place):

| Indicator | Before | After |
|---|---|---|
| `videos.length` | 0 | 30 |
| `views` sample | `""` | `"4600 views"`, `"15000 views"`, `"26000 views"` |
| `avgViewCount` | 0 | 27500 |
| `estimatedPrice` | 0 | 27500 |
| `Med Views` UI | `0` | `28K` |
| Spinner | permanent | gone |

Other platforms (TikTok, IG, Twitter): unchanged.

## Phase 5 — Report + Cleanup

1. Bug report written to `docs/bugfix-youtube-estimated-quote-loading.md` — sections: symptom, three-layer root cause, investigation log, fix diff, verification table, follow-ups.

2. Cleanup verified:
   ```
   $ grep -r "YUGU_DEBUG" .
   (no matches)
   ```
   Re-ran type-checker → `utils/youtube/index.ts` clean.

3. Follow-ups noted in report:
   - Quarterly review of `youtubei.js` version vs YouTube API changes.
   - Consider folding K/M/B handling into `extractCount` (with regression tests for TikTok / IG).
   - Sentry breadcrumb for `getYoutubeData() returns 0 videos` — catches the next regression automatically.

## Methodology takeaways

1. **Phase 0's success criterion saved us at round 3.** Without "amount must match magnitude", we would have stopped at "spinner gone" with `medianViews: 30` and shipped a worse bug.

2. **Phase 2's structured `JSON.stringify` logs** were copy-pasteable, so each round was a clean handoff: user pastes, you read, you adjust.

3. **Phase 3's chain documentation** prevented panic when each individual fix didn't fully solve it. Each level had its own piece of evidence.

4. **Phase 4's "do not touch `extractCount`"** kept blast radius minimal — three lines of YouTube-path normalization vs a global utility change that might've broken TikTok.

5. **Phase 5's grep-clean rule** meant no debug logs leaked to prod.
