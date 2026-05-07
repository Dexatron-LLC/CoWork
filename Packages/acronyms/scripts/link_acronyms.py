#!/usr/bin/env python3
"""Wikilink defined acronyms across the vault.

Idempotent. Skips frontmatter, fenced code, inline code, existing wikilinks,
markdown links, raw URLs, and the acronyms.md file itself. Only matches
whole-word ALL-CAPS tokens.

Usage:
    python link_acronyms.py [--vault PATH] [--apply] [--include GLOB]...
                            [--exclude GLOB]...

Without --apply, runs in dry-run mode and prints what *would* change.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from glossary import Glossary, default_vault_path, glossary_path  # noqa: E402

FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
WIKILINK_RE = re.compile(r"\[\[[^\]]+\]\]")
MD_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)|\[[^\]]+\]\[[^\]]*\]")
URL_RE = re.compile(r"https?://\S+|<https?://[^>]+>")

DEFAULT_EXCLUDES = (
    ".git",
    ".obsidian",
    ".trash",
    ".superpowers",
    "_archive",
)


def build_token_pattern(terms: list[str]) -> re.Pattern:
    if not terms:
        return re.compile(r"$.")
    sorted_terms = sorted(terms, key=len, reverse=True)
    escaped = [re.escape(t) for t in sorted_terms]
    return re.compile(rf"(?<![A-Za-z0-9_\-/]){'|'.join(escaped)}(?![A-Za-z0-9_\-])")


def mask_protected(text: str) -> tuple[str, list[tuple[int, int, str]]]:
    """Replace protected spans with sentinel placeholders so a regex pass
    won't match inside them. Returns the masked text and a list of (start,
    end, original) tuples to splice back later.
    """
    spans: list[tuple[int, int, str]] = []
    masked = list(text)
    for pattern in (FRONTMATTER_RE, FENCED_CODE_RE, INLINE_CODE_RE, WIKILINK_RE, MD_LINK_RE, URL_RE):
        for m in pattern.finditer(text):
            spans.append((m.start(), m.end(), m.group(0)))
    spans.sort()
    merged: list[tuple[int, int, str]] = []
    for s, e, src in spans:
        if merged and s < merged[-1][1]:
            ps, pe, psrc = merged[-1]
            if e > pe:
                merged[-1] = (ps, e, text[ps:e])
        else:
            merged.append((s, e, src))
    for s, e, _src in merged:
        for i in range(s, e):
            masked[i] = "\x00"
    return "".join(masked), merged


def link_text(text: str, pattern: re.Pattern) -> tuple[str, int]:
    masked, _ = mask_protected(text)

    def linker(m: re.Match) -> str:
        token = m.group(0)
        first = token[0].upper()
        return f"[[Acronyms/acronyms#{first}|{token}]]"

    new_masked, n = pattern.subn(linker, masked)

    out_chars = list(new_masked)
    src_chars = list(text)
    result: list[str] = []
    src_idx = 0
    masked_idx = 0
    while masked_idx < len(new_masked):
        ch = new_masked[masked_idx]
        if ch == "\x00":
            result.append(src_chars[src_idx])
            src_idx += 1
            masked_idx += 1
        elif src_idx < len(src_chars) and ch == src_chars[src_idx]:
            result.append(ch)
            src_idx += 1
            masked_idx += 1
        else:
            result.append(ch)
            masked_idx += 1
    return "".join(result), n


def iter_markdown(vault: Path, includes: list[str], excludes: list[str]) -> list[Path]:
    paths: list[Path] = []
    for p in vault.rglob("*.md"):
        rel = p.relative_to(vault)
        rel_str = rel.as_posix()
        if any(part in DEFAULT_EXCLUDES for part in rel.parts):
            continue
        if rel.parts[:1] == ("Acronyms",):
            continue
        if includes and not any(rel_str.startswith(g) or rel.match(g) for g in includes):
            continue
        if any(rel_str.startswith(g) or rel.match(g) for g in excludes):
            continue
        paths.append(p)
    return paths


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", type=Path, default=default_vault_path())
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    ap.add_argument("--include", action="append", default=[], help="Path glob to include (repeatable)")
    ap.add_argument("--exclude", action="append", default=[], help="Path glob to exclude (repeatable)")
    args = ap.parse_args()

    g = Glossary.load(glossary_path(args.vault))
    pattern = build_token_pattern(g.all_terms())

    total_files = 0
    total_changes = 0
    for path in iter_markdown(args.vault, args.include, args.exclude):
        original = path.read_text(encoding="utf-8")
        new_text, n = link_text(original, pattern)
        if n:
            total_files += 1
            total_changes += n
            rel = path.relative_to(args.vault).as_posix()
            print(f"{'WOULD LINK' if not args.apply else 'LINKED'}: {rel}  ({n} occurrences)")
            if args.apply and new_text != original:
                path.write_text(new_text, encoding="utf-8")

    verb = "would link" if not args.apply else "linked"
    print(f"\n{total_changes} occurrences across {total_files} files {verb}.")
    if not args.apply and total_changes:
        print("Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
