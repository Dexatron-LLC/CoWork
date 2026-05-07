#!/usr/bin/env python3
"""Categorize orphan files in the vault.

Walks the vault, identifies files with zero incoming links from any Markdown
source, and ensures each is linked from a `Categories/<Title Case>.md` file.

Idempotent: once linked, a file is no longer an orphan and won't be
re-processed. Append-only: never deletes content; only adds bullets under
`## Items` in the category file (creating it from a template if missing).

Usage:
    python categorize.py [--vault PATH] [--apply]

Without --apply, runs in dry-run and prints the plan.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (  # noqa: E402
    all_link_source_files,
    all_tracked_files,
    build_link_maps,
    category_for,
    default_vault,
    get_h1,
    is_orphan_candidate,
    parse_frontmatter,
    today_iso,
    upsert_category,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", type=Path, default=default_vault())
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = ap.parse_args()

    vault: Path = args.vault
    today = today_iso()

    print(f"Vault: {vault}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print()

    sources = all_link_source_files(vault)
    targets = all_tracked_files(vault)
    print(f".md files (link sources): {len(sources)}")
    print(f"Tracked files (orphan candidates pool): {len(targets)}")

    inbound, _outbound = build_link_maps(vault, sources, targets)

    candidates = [p for p in targets if is_orphan_candidate(p.relative_to(vault))]
    orphans = [p for p in candidates if not inbound.get(p.relative_to(vault).as_posix())]
    print(f"Orphan candidates: {len(candidates)}")
    print(f"Orphans (no incoming links): {len(orphans)}")

    plan: dict[str, list[Path]] = defaultdict(list)
    for p in orphans:
        if p.suffix.lower() == ".md":
            try:
                fm = parse_frontmatter(p.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, FileNotFoundError, OSError):
                continue
        else:
            fm = {}
        cat = category_for(vault, p, fm)
        plan[cat].append(p)

    print(f"\nCategorization plan ({len(plan)} categories):")
    for cat in sorted(plan, key=lambda c: (-len(plan[c]), c)):
        print(f"  {cat:35s} {len(plan[cat])}")

    actions: dict[str, int] = defaultdict(int)
    for cat, items in sorted(plan.items()):
        for orphan in items:
            display: str | None = None
            if orphan.suffix.lower() == ".md":
                try:
                    display = get_h1(orphan.read_text(encoding="utf-8"))
                except (UnicodeDecodeError, FileNotFoundError, OSError):
                    pass
            if not display:
                display = orphan.stem.replace("-", " ").replace("_", " ")
            result = upsert_category(vault, cat, orphan, display, apply=args.apply, today=today)
            actions[result] += 1

    print(f"\nActions: {dict(actions)}")
    if not args.apply:
        print("\n(dry-run; pass --apply to write changes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
