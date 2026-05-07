#!/usr/bin/env python3
"""Zip every package under Packages/ into dist/<name>.zip.

Each archive is rooted at the package name (so extracting `orphans.zip`
yields a directory called `orphans/` containing the plugin manifest, skill,
scripts, and README). Suitable for `claude --plugin-url` testing or for
attaching to a GitHub Release.

Excludes __pycache__/ and *.pyc by default. Stdlib only.

Usage:
    python bin/build-zips.py                        # zip all packages
    python bin/build-zips.py --package orphans      # one specific package
    python bin/build-zips.py --out custom-dir       # alternate output dir
    python bin/build-zips.py --clean                # rm dist/ before building
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = REPO_ROOT / "Packages"
DEFAULT_OUT = REPO_ROOT / "dist"

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def should_skip(rel_parts: tuple[str, ...], suffix: str) -> bool:
    if any(part in EXCLUDE_DIRS for part in rel_parts):
        return True
    if suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def zip_package(pkg_dir: Path, out_dir: Path) -> tuple[Path, int]:
    """Return (archive_path, file_count)."""
    archive = out_dir / f"{pkg_dir.name}.zip"
    file_count = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(pkg_dir.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(pkg_dir.parent)
            if should_skip(rel.parts, f.suffix):
                continue
            zf.write(f, rel.as_posix())
            file_count += 1
    return archive, file_count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--package",
        action="append",
        default=[],
        help="Limit to specific package(s) by name (repeatable)",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Output directory (default: {DEFAULT_OUT})")
    ap.add_argument("--clean", action="store_true", help="Remove the output directory before building")
    args = ap.parse_args()

    if not PACKAGES_DIR.is_dir():
        print(f"error: {PACKAGES_DIR} not found", file=sys.stderr)
        return 1

    if args.clean and args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True, exist_ok=True)

    packages = [p for p in sorted(PACKAGES_DIR.iterdir()) if p.is_dir() and (p / ".claude-plugin" / "plugin.json").exists()]
    if args.package:
        wanted = set(args.package)
        packages = [p for p in packages if p.name in wanted]
        missing = wanted - {p.name for p in packages}
        if missing:
            print(f"error: unknown package(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 1
    if not packages:
        print("No packages to build.", file=sys.stderr)
        return 1

    print(f"Repo: {REPO_ROOT}")
    print(f"Output: {args.out}")
    print(f"Packages: {len(packages)}")
    print()

    total_files = 0
    for pkg in packages:
        archive, count = zip_package(pkg, args.out)
        size_kb = archive.stat().st_size / 1024
        rel_archive = archive.relative_to(REPO_ROOT)
        print(f"  {pkg.name:20s} -> {rel_archive}  ({count} files, {size_kb:.1f} KB)")
        total_files += count

    print(f"\nBuilt {len(packages)} zip(s); {total_files} files total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
