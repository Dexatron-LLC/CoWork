#!/usr/bin/env python3
"""Scan the vault for ALL-CAPS tokens that are not yet in the glossary.

Outputs a report sorted by frequency, suitable for triage. Skips frontmatter,
fenced code, inline code, existing wikilinks, markdown links, raw URLs, and
the acronyms.md file itself.

Usage:
    python detect_acronyms.py [--vault PATH] [--min-count N] [--min-len N]
                              [--top N]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from glossary import (  # noqa: E402
    Glossary,
    default_vault_path,
    excluded_token,
    glossary_path,
)
from link_acronyms import DEFAULT_EXCLUDES, mask_protected  # noqa: E402

TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_\-/.])[A-Z][A-Z0-9]{1,15}(?:-[A-Z0-9]+)?(?![A-Za-z0-9_\-])")


def scan(vault: Path, min_len: int, max_len: int) -> Counter:
    counts: Counter = Counter()
    locations: dict[str, set[str]] = {}
    g = Glossary.load(glossary_path(vault))
    known = {t.upper() for t in g.all_terms()}

    for p in vault.rglob("*.md"):
        rel = p.relative_to(vault)
        if any(part in DEFAULT_EXCLUDES for part in rel.parts):
            continue
        if rel.parts[:1] == ("Acronyms",):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        masked, _ = mask_protected(text)
        for m in TOKEN_RE.finditer(masked):
            tok = m.group(0)
            if len(tok) < min_len or len(tok) > max_len:
                continue
            if tok.upper() in known:
                continue
            if excluded_token(tok):
                continue
            counts[tok] += 1
            locations.setdefault(tok, set()).add(rel.as_posix())

    counts._locations = locations  # type: ignore[attr-defined]
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", type=Path, default=default_vault_path())
    ap.add_argument("--min-count", type=int, default=2, help="Minimum occurrences to report (default: 2)")
    ap.add_argument("--min-len", type=int, default=2, help="Minimum token length (default: 2)")
    ap.add_argument("--max-len", type=int, default=8, help="Maximum token length (default: 8)")
    ap.add_argument("--top", type=int, default=50, help="Limit output to top N (default: 50)")
    ap.add_argument("--show-files", action="store_true", help="List files where each token appears")
    args = ap.parse_args()

    counts = scan(args.vault, args.min_len, args.max_len)
    locations = getattr(counts, "_locations", {})

    items = [(t, c) for t, c in counts.items() if c >= args.min_count]
    items.sort(key=lambda x: (-x[1], x[0]))

    print(f"{'TOKEN':<16} {'COUNT':<6}  FILES")
    print(f"{'-' * 16} {'-' * 6}  {'-' * 5}")
    for tok, c in items[: args.top]:
        files = locations.get(tok, set())
        if args.show_files:
            print(f"{tok:<16} {c:<6}  {', '.join(sorted(files)[:3])}{'  ...' if len(files) > 3 else ''}")
        else:
            print(f"{tok:<16} {c:<6}  ({len(files)} files)")

    print(f"\n{len(items)} undefined tokens at >= {args.min_count} occurrences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
