---
name: seo-geo-playbook
description: Audit, design, implement, and verify production-grade Technical SEO and Generative Engine Optimization (GEO / AI Search optimization for ChatGPT Search, Perplexity, Claude, Google AI Overviews, Kimi, Metaso) for web apps, multi-locale Next.js sites, SaaS products, and browser extensions ("做SEO", "GEO优化", "大模型搜索优化", "多语言SEO", "llms.txt", "sitemap/robots/hreflang/JSON-LD", "SEO验收测试"). Use when building or auditing a product website's search visibility, structured data, multilingual indexing, AI crawler endpoints, high-information-gain landing pages, or automated SEO regression gates.
---

# Product SEO & GEO Playbook

A reusable, zero-black-hat engineering and content architecture for **Technical SEO + Generative Engine Optimization (GEO)**, proven in Lumi (`islumi.com`). It combines deterministic multi-locale SSR foundations, machine-readable grounding endpoints (`/llms.txt`, `/llms-full.txt`, `sitemap.xml`, `robots.txt`, `IndexNow`), entity-disambiguating Schema.org JSON-LD, high-information-gain page templates, and a two-tier automated verification gate (`seo.test.ts` + `seo-ssr.ts`).

## 0. Four Non-Negotiable Red Lines

Enforce these rules on every project before writing copy or routes:

1. **One Search Intent = One Canonical URL (No Doorway Pages)**
   - Never generate synonym-swapped template pages (`/video-translator`, `/ai-video-translator`, `/translate-video-online`) with near-identical bodies. Map each distinct user intent and LLM prompt to a single canonical path.
2. **Evidence-Only Comparisons (No Puffery or Unverified Claims)**
   - Competitor comparison tables and feature pages must state verifiable engineering facts (supported platforms, architecture, quota numbers, BYOK policies).
   - Mark undocumented competitor internals as `Unconfirmed / 未公开说明`—never equate "undocumented" with "unsupported".
   - Always include an honest **"When to choose which"** section stating where competitors excel and where your product is the specialist choice.
3. **Zero Hidden Text or Prompt Injection**
   - Never use `display: none`, tiny fonts, or invisible text to stuff keywords or LLM instructions. Every fact in JSON-LD and `/llms.txt` must match visible SSR DOM text.
4. **Single Source of Truth for Product Facts (No Marketing Drift)**
   - Import quotas, pricing numbers, limits, and supported providers directly from core domain/config modules (`product-facts.ts`).
   - Every feature or guide page must contain real **semantic tables (`<table>`)**, **reproducible Before/After samples** (with model, temperature, and prompt hash/version provenance when applicable), or **step-by-step workflows (`<ol>`)**.

---

## Phase 1: Discovery & Intent Mapping

Before touching code, collect or define:

1. **Canonical Origin & Locales**: Production origin (e.g., `https://example.com`), supported locales (`en`, `zh-CN`, `zh-TW`, `ja`, `ko`, etc.), and `x-default` locale (typically `en`).
2. **Public vs. Private Route Manifest**:
   - **Public routes (`publicPaths`)**: `/`, `/pricing`, `/download`, `/docs`, `/support`, `/privacy`, `/terms`, `/features/[slug]`, `/compare/[slug]`, `/explore/[slug]`.
   - **Private/Auth routes**: `/workspace`, `/dashboard`, `/account`, `/library`, `/redeem`, `/login`, `/admin`.
3. **Keyword & GEO Prompt Map**:
   - Build a table mapping each public route to: (a) Page role, (b) Core SEO keywords per locale, and (c) Target natural-language LLM questions ("What extension supports bilingual subtitles on both Bilibili and YouTube?").

---

## Phase 2: Technical SEO & Multi-Locale SSR Foundation

Start from `references/nextjs-seo-foundation.ts.txt` and adapt identifiers to the target repo.

### 1. Server-Rendered `<html lang>` & Strict URL-Locale Authority
- Render `<html lang={locale}>` directly in the server `app/[locale]/layout.tsx`. Never hardcode `<html lang="zh-CN">` in a root layout and patch it via client-side `useEffect`.
- **Delete client-side `navigator.languages` auto-redirect components** on localized routes (`/[locale]/*`). When a URL already contains an explicit locale prefix, 100% respect the URL locale so `en-US` crawlers (`Googlebot`, `OAI-SearchBot`, `ClaudeBot`, `PerplexityBot`) can index `/zh-CN/*`, `/ja/*`, and `/ko/*` without being bounced to `/en/*`.
- Separate `app/global-not-found.tsx` (which renders its own `<html lang="en">` and `robots: { index: false, follow: false }`) from `app/[locale]/not-found.tsx` so 404 responses never nest `<html>` tags.

### 2. Server Component Shells & Public/Private Split
- Never put `export const dynamic = "force-dynamic"` in a shared layout. Keep static marketing/docs/feature pages pre-rendered (`SSG`), and only opt into dynamic rendering on pages that genuinely read request headers/cookies.
- Keep `/pricing`, `/download`, `/docs`, `/features/*`, `/compare/*`, and `/explore/*` as **Server Components** exporting `generateMetadata`. Extract interactive widgets (checkout buttons, copy-to-clipboard, modals, tabs) into leaf Client Components so `<h1>`, `<h2>`, `<table>`, and FAQ `<dl>` render in the initial non-JS HTML.
- Separate the public homepage (`/`) from the authenticated app (`/workspace`). The public homepage must never read user session databases, guaranteeing clean CDN caching and deterministic crawler responses.

### 3. Unified `buildPageMetadata` Helper (`app/_lib/seo.ts`)
- Centralize `publicPaths`, `featureSlugs`, `exploreSlugs`, `contentUpdatedAt`, `pageUrl(locale, pathname)`, and `languageAlternates(pathname)`.
- Deduplicate brand suffixes in `<title>`:
  ```ts
  title: { absolute: /\bBrandName\b/i.test(title) ? title : `${title} · BrandName` }
  ```
- For public pages (`noIndex = false`): emit self-referencing `alternates.canonical` and full `alternates.languages` (all supported locales + `"x-default": pageUrl("en", pathname)`), plus complete `openGraph` (`1200x630` image, localized `og:locale`) and `twitter` (`summary_large_image`).
- For private pages (`noIndex = true`): set `robots: { index: false, follow: false }` and `alternates: undefined` (never emit canonical/hreflang on `noindex` pages).

### 4. `robots.ts` — Explicit AI Crawler Allowlist + Per-Bot Private Disallow
- In `robots.txt`, any bot with its own `User-agent` block ignores the wildcard `User-agent: *` block. Therefore, attach the full `disallow` array (`["/api/", ...privateRoutes.flatMap(p => [`/*/${p}`, `/${p}`])]`) to **every** user-agent rule:
  - `*`, `OAI-SearchBot`, `ChatGPT-User`, `PerplexityBot`, `ClaudeBot`, `Claude-Web`, `Google-Extended`, `Applebot-Extended`, `Bytespider`, `YouBot`.

### 5. `sitemap.ts` — Reciprocal Multilingual Matrix & Real Modification Dates
- Cross-product `publicPaths × locales`. Attach `alternates: { languages: languageAlternates(pathname) }` to every entry.
- Assign semantic priorities: `/` (`1.0`), `/pricing` & `/download` & `/features/*` (`0.9`), `/docs` & `/compare/*` & `/explore/*` (`0.8`), `/privacy` & `/terms` (`0.4`).
- Use explicit content revision dates (`contentUpdatedAt = "YYYY-MM-DD"`), never `new Date()`.

### 6. `/llms.txt` & `/llms-full.txt` — Low-Token LLM Grounding
- Serve `text/plain; charset=utf-8` with `Cache-Control: public, max-age=3600` and `X-Content-Type-Options: nosniff`.
- `/llms.txt`: H1 product name, blockquote one-sentence entity definition, canonical website & store/download links, and a generated Markdown list of all `publicPaths` (`en`) plus optional links to reproducible sample JSON and `/llms-full.txt`.
- `/llms-full.txt`: Includes `/llms.txt` followed by structured Markdown tables generated from the same `product-facts.ts`, provider list, and feature specification/FAQ objects rendered on the site.

### 7. Safe Schema.org JSON-LD (`Organization`, `SoftwareApplication`, `FAQPage`, `LearningResource`)
- Always serialize JSON-LD with `JSON.stringify(data).replace(/</g, "\\u003c")` so `</script>` or HTML tags inside FAQ answers can never break out of `<script type="application/ld+json">`.
- Render `ProductJsonLd` (`@graph` containing `Organization` + `SoftwareApplication` with `alternateName`, `applicationCategory`, `operatingSystem`, `installUrl`, `sameAs`, and localized `offers` matching the visible pricing page) on `/`, `/pricing`, `/download`, `/features/*`, `/compare/*`, and `/explore/*`.
- Render `FaqJsonLd` from the exact same `FaqItem[]` array used to render the visible `<dl>` on the page.
- Render `LearningResource` or `Article` JSON-LD on case-study/explore pages with `isBasedOn` pointing to the source video/artifact.

### 8. `IndexNow` Instant Indexing Push
- Host a static verification route `app/[INDEXNOW_KEY].txt/route.ts` returning the 32-hex key as `text/plain`.
- Provide `scripts/submit-indexnow.ts` (`pnpm seo:indexnow` with `--dry-run` support) that posts all `sitemap()` URLs plus `/llms.txt` and `/llms-full.txt` to `https://api.indexnow.org/indexnow` immediately after deployment to notify Bing, ChatGPT Search, Perplexity, and Copilot.

---

## Phase 3: High-Information-Gain Page Architecture

Design pages so both human readers and RAG retrievers extract structured facts immediately:

1. **Hub-and-Spoke Internal Linking (`Click Depth = 1`)**:
   - The homepage (`SiteNav` + 3-column `SiteFooter`: Features & Explore / Providers & Docs / Product & Compare) must link directly to every path in `publicPaths`.
2. **Feature Landing Pages (`/[locale]/features/[slug]`)**:
   - Focused pain-point `<h1>` + mechanism summary + install CTAs.
   - Semantic `<SeoTable caption="..." headers={[...]} rows={[...]} />` with `<th scope="col">` and `<th scope="row">`.
   - Real Before/After data comparison (e.g., fragmented auto-captions vs. semantically resegmented cues) with downloadable sample JSON and run provenance.
   - 4-step workflow `<ol>` and 4 deep FAQs (`>120` chars per answer) paired with `FaqJsonLd`.
3. **Comparison Pages (`/[locale]/compare/[slug]`)**:
   - Multi-column `<SeoTable>` comparing your product with 2–3 category leaders across objective dimensions.
   - "When to choose which" decision guide + external official source links with `target="_blank" rel="noopener noreferrer"`.
4. **Curated Case Study / Explore Library (`/[locale]/explore/[slug]`)**:
   - Turn real outputs produced by the product (e.g., bilingual study guides, timestamped chapter outlines, benchmark runs) into indexable public pages targeting long-tail content queries.

---

## Phase 4: Verification (Two-Tier Automated Gate)

Never declare SEO/GEO work complete without running both test suites from `references/seo-verification-suite.ts.txt`:

1. **Tier 1 — Unit Contract Suite (`tests/seo.test.ts`)**:
   - Verifies canonical URLs and reciprocal `hreflang` matrix across all `publicPaths × locales`.
   - Verifies all private pages have `noindex, nofollow` and `alternates === undefined`.
   - Verifies every bot rule in `robots.ts` excludes private paths.
   - Verifies localized content completeness, unique titles, FAQ answer depth, brand-name deduplication, and `serializeJsonLd` script-breakout safety.
2. **Tier 2 — Live SSR Googlebot Crawler Suite (`tests/seo-ssr.ts`)**:
   - Fetches every `/${locale}${path}` with `User-Agent: Googlebot` and `redirect: "manual"`.
   - Asserts HTTP `200`, matching `<html lang="${locale}">`, unique `<title>` (single brand mention) and `<meta name="description">`, exact `<link rel="canonical">`, all `hreflang` links, OpenGraph/Twitter tags, visible `<h1>`/`<h2>`/`<table>`, 100% text parity between `FAQPage` JSON-LD and visible DOM text, homepage links to every `publicPath` (click depth 1), `noindex` on `/login` and `404` routes, `307` auth redirects on protected routes, and valid `/robots.txt`, `/sitemap.xml`, `/llms.txt`, `/llms-full.txt`, and IndexNow key endpoints.

## Pitfalls Seen in Production

- **Hardcoded `<html lang>` + client `useEffect` sync**: Non-JS AI crawlers indexed English, Japanese, and Korean pages as `zh-CN`.
- **Client-side `navigator.languages` redirect on `/[locale]/*`**: `Googlebot` (`en-US`) crawling `/zh-CN/docs` got redirected to `/en/docs`, de-indexing non-English pages.
- **Per-bot `robots.txt` blocks missing `Disallow`**: Adding `User-agent: OAI-SearchBot` with `Allow: /` without repeating the `Disallow` list unintentionally allowed AI bots to crawl `/api/` and private routes.
- **Duplicate brand names in `<title>`**: Appending ` · Brand` blindly produced `Brand — Video Assistant · Brand`. Use a word-boundary regex check before appending.
- **Root `force-dynamic` or top-level `"use client"` on marketing pages**: Prevented `generateMetadata` export and broke static pre-rendering.
- **Nested `<html>` on 404 pages**: Moving `<html lang={locale}>` into `app/[locale]/layout.tsx` requires `app/global-not-found.tsx` to own its own `<html>` while `app/[locale]/not-found.tsx` renders only the inner scene.
