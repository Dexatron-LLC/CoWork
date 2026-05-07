#!/usr/bin/env python3
"""Log orphan and deadend counts to a stamped file for trend analysis.

Each invocation appends a single JSON line to `<state-dir>/trend.jsonl` with
counts and a timestamp, so the trajectory of vault orphan counts can be
reviewed over time. With `--show`, prints the recent history instead.

Default state dir: `~/.local/share/cowork-orphans/` (override with
`--state-dir` or the `COWORK_ORPHANS_STATE` env var).

Usage:
    python trend.py                         # log a new sample
    python trend.py --show                  # show recent history
    python trend.py --show --last 10        # show only the most recent 10
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
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


def default_state_dir() -> Path:
    env = os.environ.get("COWORK_ORPHANS_STATE")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "cowork-orphans"


def sample(vault: Path) -> dict[str, object]:
    sources = all_link_source_files(vault)
    targets = all_tracked_files(vault)
    inbound, outbound = build_link_maps(vault, sources, targets)

    candidates = [p for p in targets if is_orphan_candidate(p.relative_to(vault))]
    orphan_count = sum(
        1 for p in candidates if not inbound.get(p.relative_to(vault).as_posix())
    )
    deadend_count = sum(
        1
        for p in sources
        if is_orphan_candidate(p.relative_to(vault))
        and not outbound.get(p.relative_to(vault).as_posix())
    )

    return {
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "vault": str(vault),
        "sources": len(sources),
        "tracked": len(targets),
        "candidates": len(candidates),
        "orphans": orphan_count,
        "deadends": deadend_count,
    }


def show(state_path: Path, last: int) -> int:
    if not state_path.exists():
        print(f"No history yet at {state_path}.")
        return 0
    lines = state_path.read_text(encoding="utf-8").splitlines()
    if last > 0:
        lines = lines[-last:]
    print(f"{'timestamp':<20} {'orphans':>8} {'deadends':>9} {'sources':>8} {'candidates':>11}")
    print(f"{'-' * 20} {'-' * 8} {'-' * 9} {'-' * 8} {'-' * 11}")
    for line in lines:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        print(
            f"{r.get('ts', '')[:19]:<20} "
            f"{r.get('orphans', 0):>8} "
            f"{r.get('deadends', 0):>9} "
            f"{r.get('sources', 0):>8} "
            f"{r.get('candidates', 0):>11}"
        )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", type=Path, default=default_vault())
    ap.add_argument("--state-dir", type=Path, default=default_state_dir())
    ap.add_argument("--show", action="store_true", help="Show recent history instead of sampling")
    ap.add_argument("--last", type=int, default=20, help="With --show: limit to most recent N")
    ap.add_argument("--no-print", action="store_true", help="Suppress the new-sample echo")
    args = ap.parse_args()

    state_path = args.state_dir / "trend.jsonl"

    if args.show:
        return show(state_path, args.last)

    record = sample(args.vault)
    args.state_dir.mkdir(parents=True, exist_ok=True)
    with state_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    if not args.no_print:
        print(json.dumps(record, indent=2))
        print(f"\nAppended to {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
