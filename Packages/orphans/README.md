# cowork-orphans

A CoWork package for vault link hygiene. Supersedes the vault-side `Scripts/categorize_orphans.py`.

## What it does

Four actions, all dispatched from the `orphans` skill:

- **`categorize`** — the canonical pass. Finds files with zero inbound links and adds a bullet under `Categories/<X>.md` per the 6-level category-resolution priority. Append-only, idempotent.
- **`deadends`** — Markdown notes with zero outbound links. Read-only report.
- **`promote`** — files whose only inbound link is from a `Categories/` file. The "auto-categorized but not thought about" pile. Read-only report.
- **`trend`** — per-run orphan and deadend counts logged to a JSONL file for trend review.

The hard rules (category priority, exclusion model, wikilink form, Obsidian-style resolution) are encoded in `skills/orphans/SKILL.md` and enforced by `scripts/lib.py`.

## Layout

```
.claude-plugin/plugin.json       # plugin manifest
skills/orphans/SKILL.md          # umbrella skill
scripts/
    lib.py                       # shared: vault detection, link parsing,
                                 #   resolution, exclusion model, category
                                 #   rules, file rendering, idempotent upsert
    categorize.py                # canonical pass (writes Categories/*.md)
    deadends.py                  # outbound-orphan report (read-only)
    promote.py                   # Categories-only-link report (read-only)
    trend.py                     # log + show counts over time
```

## Vault path

Default: `/mnt/d/Dropbox/Vault`. Override per-call with `--vault PATH`, or globally via `COWORK_VAULT` (also accepts the legacy `VAULT` env var for back-compat with the vault-side script).

## CLI usage (without the skill)

```bash
cd Packages/orphans

# Preview what categorize would do
python scripts/categorize.py

# Apply
python scripts/categorize.py --apply

# Read-only reports
python scripts/deadends.py --top 50
python scripts/promote.py --by-category --show-stem

# Trend logging
python scripts/trend.py             # log a sample
python scripts/trend.py --show      # review history
```

## Migration from the vault-side script

This package replaces `D:\Dropbox\Vault\Scripts\categorize_orphans.py` and the `/categorize-orphans` slash command. Recommended retirement sequence (do these only after parity is confirmed):

1. Run `categorize.py --apply` and verify the resulting `Categories/*.md` diff matches what the vault script would have produced.
2. Delete the vault-side `Scripts/categorize_orphans.py` (use the Obsidian CLI from PowerShell — the bash sandbox can't `rm` inside the FUSE-mounted vault).
3. Update or delete `D:\Dropbox\Vault\.claude\commands\categorize-orphans.md`.
4. Update the `Categories` and orphan-related sections in `D:\Dropbox\Vault\CLAUDE.md` to reference this package.

The package was designed to preserve every behavior of the vault script — porting was the whole point. New capabilities (`deadends`, `promote`, `trend`) are additive and don't touch the original code path.

## Requirements

- Python 3.10+. Standard library only — no third-party dependencies.
