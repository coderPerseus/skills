# seo-geo-playbook

Portable agent skill: audit, design, implement, and verify full-stack **Technical SEO + Generative Engine Optimization (GEO)** for web apps, SaaS products, and browser extensions. Works in **Claude Code** and **OpenAI Codex CLI** from one source tree.

Proven in Lumi (`islumi.com`): 5 locales × 16 public routes (80 pre-rendered/SSR URLs), reciprocal `hreflang` matrix, AI-bot-aware `robots.txt`, `/llms.txt` & `/llms-full.txt`, entity-disambiguating Schema.org JSON-LD (`Organization` + `SoftwareApplication` + `FAQPage` + `LearningResource`), `IndexNow` instant push, high-information-gain feature/comparison/explore pages, and a two-tier automated verification gate.

## What the skill covers

- **Four Red Lines**: 1 search intent = 1 canonical URL (no doorway pages), evidence-only comparisons with "When to choose which", zero hidden text/prompt injection, and single source of truth for numeric product facts
- **Multi-locale SSR foundation**: server-rendered `<html lang={locale}>`, strict URL-locale authority (no client `navigator.languages` redirect on localized routes), Server Component shells, and public `/` vs. private `/workspace` separation
- **Machine-readable endpoints**: `buildPageMetadata`, `robots.ts` (explicit rules for `OAI-SearchBot`, `PerplexityBot`, `ClaudeBot`, `Google-Extended`, etc.), `sitemap.ts`, `/llms.txt`, `/llms-full.txt`, and `IndexNow` verification + submission script
- **Safe Schema.org JSON-LD**: `\u003c`-escaped serialization, `@graph` (`Organization` + `SoftwareApplication`), `FAQPage` with strict visible-DOM parity, and `LearningResource`
- **Two-tier automated verification**: `seo.test.ts` (unit contracts) + `seo-ssr.ts` (real HTTP `Googlebot` non-JS crawler assertions across all locales and routes)

## Layout

```
skills/seo-geo-playbook/
├── SKILL.md                                  # agent contract
├── README.md                                 # this file
├── references/
│   ├── nextjs-seo-foundation.ts.txt          # seo.ts, robots.ts, sitemap.ts, llms.ts, json-ld, seo-table, indexnow
│   └── seo-verification-suite.ts.txt         # seo.test.ts (unit contracts) + seo-ssr.ts (live Googlebot SSR crawler)
└── scripts/
    └── install.sh
```

## Install

```bash
./skills/seo-geo-playbook/scripts/install.sh
```

Then ask for it: "给这个项目做一套完整的 SEO 和 GEO 优化", "add llms.txt, sitemap, JSON-LD and SEO SSR tests".
