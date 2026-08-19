# pdf-to-epub

Portable agent skill: convert a PDF book to a reflowable EPUB. Works in **Claude Code** and **OpenAI Codex CLI** from one source tree.

Calibre keeps visual line breaks, running headers, and watermarks. This skill strips those, rebuilds paragraphs, and splits chapters from PDF bookmarks or running headers.

## What it does

`scripts/pdf_to_epub.py` is the converter. It is **not** tied to any one book:

1. Measure how many pages have a real text layer. Scans exit 2.
2. Detect running headers/footers/watermarks by frequency and line shape (`12 // …`, `… // 12`, repeated last lines).
3. Split chapters: PDF outline/bookmarks → else header-title changes → else a single chapter.
4. Reflow broken lines (CJK without extra spaces).
5. Write EPUB (cover + images + NCX/nav).

## Layout

```
skills/pdf-to-epub/
├── SKILL.md                 # agent contract
├── README.md                # this file
├── requirements.txt
└── scripts/
    ├── pdf_to_epub.py       # converter CLI
    └── install.sh
```

## CLI

```bash
python3 -m pip install -r requirements.txt
python3 scripts/pdf_to_epub.py book.pdf -o book.epub
python3 scripts/pdf_to_epub.py book.pdf --inspect
```

| Flag | Meaning |
|---|---|
| `-o PATH` | Output EPUB (default: `book.epub` next to the PDF) |
| `--title` / `--author` | Override metadata ( `--author` repeatable) |
| `--inspect` | Print JSON plan, do not write |
| `--min-text-ratio` | Scan threshold (default `0.45`) |

Exit `2` with `"error": "scanned_pdf"` means OCR is required (e.g. pdf-craft), not this script.

## Install

Repo-wide:

```bash
./scripts/install.sh --only pdf-to-epub
```

This skill only:

```bash
./skills/pdf-to-epub/scripts/install.sh
```

Symlinks into `~/.claude/skills/pdf-to-epub` and `~/.agents/skills/pdf-to-epub`.

## Trigger

- "把这本 PDF 转成 EPUB" / "PDF 转电子书"
- "convert this PDF to EPUB"
- "Calibre 转完断行很乱"
- `/pdf-to-epub`

## Compatibility

Cross-tool subset only: frontmatter `name` + `description`, plain Markdown, relative paths. No `${CLAUDE_SKILL_DIR}`, no `` !`command` `` blocks, no tool-specific frontmatter.

## License

MIT.
