#!/usr/bin/env python3
"""Add a new entry to the vault Acronyms glossary.

Inserts into the correct letter section in alphabetical order, bumps the
frontmatter `updated:` field, and refuses to clobber an existing entry.
Use `--pending` when the definition is unknown.

Usage:
    python add_acronym.py --term API --definition "Application Programming Interface"
    python add_acronym.py --pending DON
    python add_acronym.py --pending FOO --note "Embertide notification context"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from glossary import (  # noqa: E402
    Glossary,
    default_vault_path,
    excluded_token,
    glossary_path,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", type=Path, default=default_vault_path())
    ap.add_argument("--term", help="Acronym to add (case-preserved)")
    ap.add_argument("--definition", help="Full definition; required unless --pending")
    ap.add_argument("--pending", help="Term to park in the Pending section")
    ap.add_argument("--note", default="", help="Optional note for the Pending entry")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.term and not args.pending:
        ap.error("Provide --term/--definition or --pending.")
    if args.term and not args.definition:
        ap.error("--term requires --definition.")

    target = args.term or args.pending
    assert target is not None
    if excluded_token(target):
        print(
            f"Refusing: '{target}' falls into an excluded category "
            "(LinkedIn code, unit symbol, date/version marker, or generic English initialism).",
            file=sys.stderr,
        )
        return 2

    g = Glossary.load(glossary_path(args.vault))

    if args.term:
        added = g.add_entry(args.term, args.definition or "")
        action = "Added" if added else "Already present"
        print(f"{action}: **{args.term}** - {args.definition}")
    else:
        added = g.add_pending(args.pending or "", args.note)
        action = "Parked in Pending" if added else "Already present (skipped)"
        print(f"{action}: **{args.pending}**")

    if added and not args.dry_run:
        g.save()
        print(f"Wrote {g.path}")
    elif args.dry_run:
        print("[dry-run] not writing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
