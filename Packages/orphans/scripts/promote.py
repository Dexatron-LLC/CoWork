#!/usr/bin/env python3
"""Find files whose only inbound link is from a `Categories/` file.

These are notes that have been auto-categorized but otherwise dead — no
real Wiki entry, no MOC, no other note references them. They are the
hidden orphans the categorize pass already "fixed" but that haven't been
*thought about* yet.

Output is a sorted report grouped by Category, with paths suitable for
copy-paste into a follow-up promotion pass (e.g. add a wikilink from a
Wiki note, then optionally remove the Categories entry).

Read-only. Writes nothing.

Usage:
    python promote.py [--vault PATH] [--by-category] [--show-stem]
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
    default_vault,
    is_orphan_candidate,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", type=Path, default=default_vault())
    ap.add_argument(
        "--by-category",
        action="store_true",
        help="Group output by the Category file that links each candidate",
    )
    ap.add_argument(
        "--show-stem",
        action="store_true",
        help="Also print the file's stem alongside its path",
    )
    args = ap.parse_args()

    vault: Path = args.vault

    sources = all_link_source_files(vault)
    targets = all_tracked_files(vault)
    inbound, _outbound = build_link_maps(vault, sources, targets)

    candidates: list[tuple[Path, str]] = []
    for target_posix, sources_set in inbound.items():
        if len(sources_set) != 1:
            continue
        sole_src = next(iter(sources_set))
        if not sole_src.startswith("Categories/"):
            continue
        target_path = vault / target_posix
        if not target_path.exists():
            continue
        if not is_orphan_candidate(Path(target_posix)):
            continue
        candidates.append((target_path, sole_src))

    candidates.sort(key=lambda x: (x[1], x[0].relative_to(vault).as_posix()))

    print(f"Vault: {vault}")
    print(f"Candidates (inbound only from Categories/): {len(candidates)}")
    print()

    if args.by_category:
        grouped: dict[str, list[Path]] = defaultdict(list)
        for target, src in candidates:
            grouped[src].append(target)
        for src in sorted(grouped):
            print(f"## {src}  ({len(grouped[src])} candidates)")
            for t in sorted(grouped[src], key=lambda p: p.relative_to(vault).as_posix()):
                rel = t.relative_to(vault).as_posix()
                if args.show_stem:
                    print(f"  - {rel}    [stem: {t.stem}]")
                else:
                    print(f"  - {rel}")
            print()
    else:
        for target, src in candidates:
            rel = target.relative_to(vault).as_posix()
            label = f"  [stem: {target.stem}]" if args.show_stem else ""
            print(f"  {rel}    (only linked from: {src}){label}")

    print()
    print("Promotion guidance: pick a candidate, write or extend a Wiki note that")
    print("references it (or add a wikilink from a relevant MOC), then optionally")
    print("remove the bullet from the Categories file once the real link is in place.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
