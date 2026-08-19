---
name: pdf-to-epub
description: Convert a PDF book into a reflowable EPUB (strip running headers/footers/watermarks, rebuild paragraphs, split chapters). Use when the user asks to 转 EPUB / PDF 转电子书 / convert PDF to EPUB / Calibre 效果不好 / 扫描件转 EPUB, or runs /pdf-to-epub.
---

# pdf-to-epub

Turn a PDF book into a reflowable EPUB. Prefer the bundled converter over Calibre for Chinese/English **text-layer** books. Do not hardcode page maps or book-specific regexes — the script is the converter.

## When to use

- "把这本 PDF 转成 EPUB"
- "PDF 转电子书 / convert this PDF to EPUB"
- "Calibre 转完断行/页眉很乱"
- Explicit `/pdf-to-epub`

Do **not** use for: PDF form filling, merging PDFs, Markdown→EPUB, or "turn this book into a study skill".

## Convert

Resolve `scripts/pdf_to_epub.py` from this skill directory (the folder that contains this `SKILL.md`).

```bash
python3 -m pip install -r requirements.txt
python3 scripts/pdf_to_epub.py "/path/to/book.pdf" -o "/path/to/book.epub"
```

Optional: `--title` `--author` (repeatable) `--inspect` (JSON plan, no write).

The script prints JSON: `text_ratio`, `chapter_source` (`bookmarks` | `running-headers` | `single`), chapter titles, output path.

## Decision tree

1. Locate the PDF. Default EPUB path: same directory, `.epub` suffix.
2. Run the converter (or `--inspect` first on huge/unknown files).
3. **Exit 0** — report the EPUB path, chapter count, and `chapter_source`. Do not open-and-review unless the user asks.
4. **Exit 2 / `scanned_pdf`** — most pages have no text layer. Tell the user this path cannot OCR. Offer pdf-craft (OCR + optional LLM) as a slow alternative; do not silently run a multi-hour job without saying so.
5. **Other non-zero** — paste the stderr/JSON and stop.

Never rebuild the EPUB with a per-book page table in the agent prompt. If chapter splits are wrong, inspect JSON (`chapter_source`, ranges) and re-run with `--title`/`--author`, or fix the script.

## What the converter already does

Owned by `scripts/pdf_to_epub.py`:

- Reject scans below `--min-text-ratio` (default 0.45)
- Drop running headers/footers/watermarks by **frequency and shape**, not book-specific strings
- Split chapters: PDF bookmarks first, else running-header title changes, else one chapter
- Reflow line-broken paragraphs (CJK joins without extra spaces)
- Cover from page 1 when it is image-heavy; embed large images

## Limits

Digital textbooks with a text layer are in scope. Scans, vertical typesetting, and heavy two-column academic layout will degrade or be rejected. That is expected.
