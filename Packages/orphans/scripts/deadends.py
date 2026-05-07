#!/usr/bin/env python3
"""Find deadend notes — Markdown files with zero outgoing links.

The complement of orphan detection: a deadend is a `.md` file whose body
contains no resolvable wikilink, embed, or markdown-link reference to any
other vault file. Such notes are dead in the other direction — readers
arriving at them find no way out.

Read-only. Writes nothing to the vault. Output is a sorted report.

Usage:
    python deadends.py [--vault PATH] [--include-attachments] [--top N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (  # noqa: E402
    all_link_source_files,
    all_tracked_files,
    build_link_maps,
    default_vault,
    is_orphan_candidate,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", type=Path, default=default_vault())
    ap.add_argument(
        "--include-categories",
        action="store_true",
        help="Include Categories/ files (normally excluded as soft-excluded top-level)",
    )
    ap.add_argument("--top", type=int, default=0, help="Limit output to top N files (0 = all)")
    args = ap.parse_args()

    vault: Path = args.vault

    sources = all_link_source_files(vault)
    targets = all_tracked_files(vault)
    _inbound, outbound = build_link_maps(vault, sources, targets)

    deadends: list[Path] = []
    for src in sources:
        rel = src.relative_to(vault)
        if not args.include_categories and not is_orphan_candidate(rel):
            continue
        rel_posix = rel.as_posix()
        if not outbound.get(rel_posix):
            deadends.append(src)

    deadends.sort(key=lambda p: p.relative_to(vault).as_posix())
    total = len(deadends)
    shown = deadends[: args.top] if args.top > 0 else deadends

    print(f"Vault: {vault}")
    print(f".md sources scanned: {len(sources)}")
    if args.top > 0 and total > args.top:
        print(f"Deadend notes (no outgoing links): {total}  (showing first {args.top})")
    else:
        print(f"Deadend notes (no outgoing links): {total}")
    print()
    for p in shown:
        rel = p.relative_to(vault).as_posix()
        size = p.stat().st_size
        print(f"  {rel}  ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
