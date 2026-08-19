#!/usr/bin/env python3
"""Convert a digital (text-layer) PDF book into a reflowable EPUB.

General converter: no book-specific page maps, header regexes, or titles.
Chapter splits prefer PDF bookmarks, then running-header title changes.
Scanned PDFs are rejected with exit code 2 — they need OCR, not this path.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

try:
    import pymupdf
except ImportError:
    sys.exit("Missing pymupdf. Install with: pip install pymupdf ebooklib")

try:
    from ebooklib import epub
except ImportError:
    sys.exit("Missing ebooklib. Install with: pip install pymupdf ebooklib")


LEAD_SEP = re.compile(r"^\d{1,4}\s*(?://|\||·|•)\s+\S")
TRAIL_SEP = re.compile(r"\S\s*(?://|\||·|•)\s+\d{1,4}\s*$")
ONLY_NUM = re.compile(r"^\d{1,4}$")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+")
WATERMARKISH = re.compile(r"(专享|尊重版权|仅供.+使用|copyright|all rights reserved)", re.I)
TITLE_ECHO = re.compile(
    r"^(前言|序言|目录|contents|preface|第\s*\d+\s*章.*|chapter\s+\d+.*|"
    r"附录\s*\d*.*|appendix.*|参考文献|bibliography|人名对照|索引|index)\s*$",
    re.I,
)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class Page:
    index: int
    lines: list[str]
    raw: str
    useful: int
    header: str | None = None
    footer: str | None = None
    header_title: str | None = None
    image_xrefs: list[int] = field(default_factory=list)


@dataclass
class Chapter:
    title: str
    start: int
    end: int


def useful_count(text: str) -> int:
    n = 0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or ch.isascii() and (ch.isalnum() or ch.isspace()):
            n += 1
    return n


def is_garbage(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 8:
        return False
    useful = useful_count(stripped)
    return useful / max(len(stripped), 1) < 0.25


def fingerprint(line: str) -> str:
    s = EMAIL.sub("EMAIL", line.strip())
    s = re.sub(r"\d+", "N", s)
    return re.sub(r"\s+", " ", s)


def header_shape(line: str) -> str | None:
    s = line.strip()
    if LEAD_SEP.match(s):
        return "lead_sep"
    if TRAIL_SEP.search(s):
        return "trail_sep"
    if ONLY_NUM.match(s):
        return "only_num"
    return None


def title_from_header(line: str) -> str | None:
    s = line.strip()
    m = re.match(r"^\d{1,4}\s*(?://|\||·|•)\s+(.+)$", s)
    if m:
        s = m.group(1).strip()
    else:
        m = re.match(r"^(.+?)\s*(?://|\||·|•)\s+\d{1,4}$", s)
        if m:
            s = m.group(1).strip()
        else:
            return None
    if WATERMARKISH.search(s) or EMAIL.search(s):
        return None
    s = re.sub(r"\s+", " ", s).strip(" /|·•")
    return s or None


def collect_pages(doc: pymupdf.Document) -> list[Page]:
    pages: list[Page] = []
    for i, page in enumerate(doc):
        raw = page.get_text("text")
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        xrefs = [info[0] for info in page.get_images(full=True)]
        pages.append(
            Page(
                index=i,
                lines=lines,
                raw=raw,
                useful=useful_count(raw),
                image_xrefs=xrefs,
            )
        )
    return pages


def text_ratio(pages: list[Page]) -> float:
    if not pages:
        return 0.0
    return sum(1 for p in pages if p.useful >= 40) / len(pages)


def detect_running_lines(pages: list[Page]) -> tuple[set[str], set[str]]:
    """Return (first-line shapes to strip, footer fingerprints to strip)."""
    text_pages = [p for p in pages if p.useful >= 40 and p.lines]
    n = max(len(text_pages), 1)

    shapes: Counter[str] = Counter()
    first_fp: Counter[str] = Counter()
    last_fp: Counter[str] = Counter()
    for p in text_pages:
        first, last = p.lines[0], p.lines[-1]
        shape = header_shape(first)
        if shape:
            shapes[shape] += 1
        first_fp[fingerprint(first)] += 1
        last_fp[fingerprint(last)] += 1
        if len(p.lines) > 1:
            last_fp[fingerprint(p.lines[-2])] += 1

    first_shapes = {shape for shape, count in shapes.items() if count / n >= 0.20}
    footers = {fp for fp, c in last_fp.items() if c / n >= 0.18 and fp}
    for fp, c in first_fp.items():
        if c / n >= 0.35:
            footers.add(fp)
    return first_shapes, footers


def apply_stripping(pages: list[Page], first_shapes: set[str], footers: set[str]) -> None:
    for p in pages:
        lines = list(p.lines)
        if not lines:
            continue
        if header_shape(lines[0]) in first_shapes:
            p.header = lines[0]
            p.header_title = title_from_header(lines[0])
            lines = lines[1:]
        while lines and fingerprint(lines[0]) in footers:
            if p.header is None:
                p.header = lines[0]
                p.header_title = p.header_title or title_from_header(lines[0])
            lines = lines[1:]
        while lines and (
            fingerprint(lines[-1]) in footers
            or WATERMARKISH.search(lines[-1])
            or (EMAIL.search(lines[-1]) and len(lines[-1]) < 80)
        ):
            p.footer = lines[-1]
            lines = lines[:-1]
        p.lines = lines


def chapters_from_bookmarks(doc: pymupdf.Document) -> list[Chapter]:
    toc = doc.get_toc(simple=True) or []
    if len(toc) < 2:
        return []
    levels = [lvl for lvl, _, _ in toc]
    top = min(levels)
    entries = [(title.strip(), max(page, 1) - 1) for lvl, title, page in toc if lvl == top and title.strip()]
    if len(entries) < 2:
        return []
    # skip degenerate bookmarks that all point at page 0/1
    pages = {e[1] for e in entries}
    if len(pages) < 2:
        return []
    chapters: list[Chapter] = []
    for i, (title, start) in enumerate(entries):
        end = entries[i + 1][1] - 1 if i + 1 < len(entries) else doc.page_count - 1
        if end < start:
            end = start
        chapters.append(Chapter(title=title, start=start, end=end))
    return chapters


def chapters_from_headers(pages: list[Page]) -> list[Chapter]:
    titled: list[tuple[int, str]] = []
    for p in pages:
        if not p.header_title:
            continue
        title = re.sub(r"\s+", " ", p.header_title)
        if WATERMARKISH.search(title) or EMAIL.search(title):
            continue
        titled.append((p.index, title))
    if len({t for _, t in titled}) < 2:
        return []

    runs: list[Chapter] = []
    current_title: str | None = None
    run_start: int | None = None
    last_idx: int | None = None
    for idx, title in titled:
        if title != current_title:
            if current_title is not None and run_start is not None and last_idx is not None:
                runs.append(Chapter(title=current_title, start=run_start, end=last_idx))
            current_title = title
            run_start = idx
        last_idx = idx
    if current_title is not None and run_start is not None and last_idx is not None:
        runs.append(Chapter(title=current_title, start=run_start, end=last_idx))

    if len(runs) < 2:
        return []

    # extend each run to the page before the next run; front matter stays its own chapter
    filled: list[Chapter] = []
    first = runs[0]
    if first.start > 0:
        filled.append(Chapter(title="文前", start=0, end=first.start - 1))
    for i, ch in enumerate(runs):
        end = runs[i + 1].start - 1 if i + 1 < len(runs) else pages[-1].index
        filled.append(Chapter(title=ch.title, start=ch.start, end=max(end, ch.start)))
    return filled


def should_join(prev: str, nxt: str, cjk: bool) -> bool:
    if not prev or not nxt:
        return False
    if TITLE_ECHO.match(re.sub(r"\s+", "", prev)) or TITLE_ECHO.match(re.sub(r"\s+", "", nxt)):
        return False
    if re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]|^\d+\.\s+\S", nxt):
        return False
    end = prev[-1]
    if end in "。！？：；…!?":
        return False
    if (not cjk) and end in ".!?:;":
        return False
    return True


def reflow(lines: list[str], cjk: bool) -> list[str]:
    paras: list[str] = []
    buf = ""
    for line in lines:
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not line:
            continue
        compact = re.sub(r"\s+", "", line)
        if TITLE_ECHO.match(compact) and buf:
            paras.append(buf)
            buf = ""
            continue
        if not buf:
            buf = line
            continue
        if should_join(buf, line, cjk):
            if buf[-1].isascii() and line[0].isascii():
                buf = f"{buf} {line}"
            else:
                buf += line
        else:
            paras.append(buf)
            buf = line
    if buf:
        paras.append(buf)
    return paras


def extract_png(doc: pymupdf.Document, xref: int) -> bytes | None:
    try:
        pix = pymupdf.Pixmap(doc, xref)
        if pix.n >= 5:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        if pix.width < 80 or pix.height < 80:
            return None
        return pix.tobytes("png")
    except Exception:
        return None


def build_epub(
    doc: pymupdf.Document,
    pages: list[Page],
    chapters: list[Chapter],
    out: Path,
    title: str,
    authors: list[str],
    language: str,
) -> dict:
    book = epub.EpubBook()
    book.set_identifier(f"pdf-to-epub-{out.stem}")
    book.set_title(title)
    book.set_language(language)
    for author in authors:
        if author:
            book.add_author(author)

    used_xrefs: set[int] = set()
    first = doc[0]
    if first.get_images() or useful_count(first.get_text("text")) < 40:
        cover = first.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")
        book.set_cover("images/cover.png", cover)
        used_xrefs.update(info[0] for info in first.get_images(full=True))

    img_n = 0
    spine: list = ["nav"]
    toc_items: list = []
    cjk = language.startswith("zh")

    for i, ch in enumerate(chapters, 1):
        lines: list[str] = []
        img_tags: list[str] = []
        for p in pages:
            if p.index < ch.start or p.index > ch.end:
                continue
            if is_garbage(p.raw) and not p.image_xrefs:
                continue
            lines.extend(p.lines)
            for xref in p.image_xrefs:
                if xref in used_xrefs:
                    continue
                blob = extract_png(doc, xref)
                if not blob:
                    continue
                used_xrefs.add(xref)
                img_n += 1
                name = f"images/fig_{img_n}.png"
                book.add_item(
                    epub.EpubItem(
                        uid=f"fig{img_n}",
                        file_name=name,
                        media_type="image/png",
                        content=blob,
                    )
                )
                img_tags.append(f'<p class="img"><img src="{name}" alt=""/></p>')

        paras = reflow(lines, cjk=cjk)
        if not paras and not img_tags:
            continue
        file_name = f"chap_{i:02d}.xhtml"
        item = epub.EpubHtml(title=ch.title, file_name=file_name, lang=language)
        parts = [f"<h1>{html.escape(ch.title)}</h1>"]
        parts.extend(f"<p>{html.escape(p)}</p>" for p in paras)
        parts.extend(img_tags)
        item.content = "\n".join(parts)
        book.add_item(item)
        spine.append(item)
        toc_items.append(item)

    if len(spine) == 1:
        raise RuntimeError("No extractable chapter content")

    book.toc = toc_items
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.add_item(
        epub.EpubItem(
            uid="style",
            file_name="style/default.css",
            media_type="text/css",
            content=(
                "body{font-family:serif;line-height:1.75;}"
                "h1{font-size:1.35em;margin:1.1em 0 .7em;}"
                "p{text-indent:2em;margin:.55em 0;}"
                "p.img{text-indent:0;text-align:center;margin:1em 0;}"
                "img{max-width:100%;height:auto;}"
            ).encode("utf-8"),
        )
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(out, book)
    return {
        "epub": str(out),
        "bytes": out.stat().st_size,
        "chapters": [ch.title for ch in chapters],
        "images": img_n,
    }


def guess_title(doc: pymupdf.Document, pdf: Path) -> str:
    meta = doc.metadata or {}
    title = (meta.get("title") or "").strip()
    if title:
        return title
    return pdf.stem


def guess_authors(doc: pymupdf.Document) -> list[str]:
    meta = doc.metadata or {}
    author = (meta.get("author") or "").strip()
    if not author:
        return []
    return [part.strip() for part in re.split(r"[;；,/]+", author) if part.strip()]


def guess_language(pages: list[Page]) -> str:
    cjk = sum(len(CJK_RE.findall(p.raw)) for p in pages)
    ascii_letters = sum(sum(1 for ch in p.raw if ch.isascii() and ch.isalpha()) for p in pages)
    return "zh" if cjk >= ascii_letters else "en"


def plan_chapters(doc: pymupdf.Document, pages: list[Page]) -> tuple[str, list[Chapter]]:
    bookmarks = chapters_from_bookmarks(doc)
    if bookmarks:
        return "bookmarks", bookmarks
    headers = chapters_from_headers(pages)
    if headers:
        return "running-headers", headers
    return "single", [Chapter(title=guess_title(doc, Path("book.pdf")), start=0, end=pages[-1].index)]


def inspect_payload(
    pdf: Path,
    pages: list[Page],
    ratio: float,
    first_shape: str | None,
    source: str,
    chapters: list[Chapter],
    scanned: bool,
) -> dict:
    return {
        "pdf": str(pdf),
        "pages": len(pages),
        "text_ratio": round(ratio, 3),
        "scanned": scanned,
        "header_shape": first_shape,
        "chapter_source": source,
        "chapters": [{"title": c.title, "start": c.start + 1, "end": c.end + 1} for c in chapters],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a text-layer PDF book to EPUB")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--author", action="append", default=[])
    parser.add_argument("--inspect", action="store_true", help="print plan as JSON, do not write EPUB")
    parser.add_argument("--min-text-ratio", type=float, default=0.45)
    args = parser.parse_args()

    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file():
        print(f"not a file: {pdf}", file=sys.stderr)
        return 1

    doc = pymupdf.open(pdf)
    pages = collect_pages(doc)
    ratio = text_ratio(pages)
    scanned = ratio < args.min_text_ratio
    first_shapes, footers = detect_running_lines(pages)
    apply_stripping(pages, first_shapes, footers)
    source, chapters = plan_chapters(doc, pages)

    payload = inspect_payload(
        pdf,
        pages,
        ratio,
        ",".join(sorted(first_shapes)) or None,
        source,
        chapters,
        scanned,
    )
    if args.inspect:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 2 if scanned else 0

    if scanned:
        json.dump(
            {
                "error": "scanned_pdf",
                "message": "Most pages have no extractable text. Use an OCR pipeline (pdf-craft), not this converter.",
                **payload,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        print()
        return 2

    out = args.output or pdf.with_suffix(".epub")
    out = out.expanduser().resolve()
    title = args.title or guess_title(doc, pdf)
    authors = args.author or guess_authors(doc)
    language = guess_language(pages)
    result = build_epub(doc, pages, chapters, out, title, authors, language)
    json.dump({**payload, **result, "title": title, "authors": authors, "language": language}, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
