# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

CoWork is the **verb layer** for Dexter's Obsidian vault at `/mnt/d/Dropbox/Vault` (Windows: `D:\Dropbox\Vault`). The vault holds the Markdown content; this repo holds the executable tooling that reads, writes, and reports on it. Each capability is one self-contained package under `Packages/<name>/`, driven by a Claude Code skill.

This file is the index. The substantive rules for each package live in that package's `skills/<name>/SKILL.md` — keep this file short, push details there.

## Layout

Monorepo. Each package follows the same shape:

```
Packages/<name>/
├── .claude-plugin/plugin.json   # manifest (name: cowork-<name>)
├── README.md                    # usage + rationale
├── skills/<name>/SKILL.md       # umbrella skill — rules + action dispatch
└── scripts/                     # Python implementation; stdlib only
    ├── lib.py                   # shared utilities (when >1 script needs them)
    └── <action>.py              # one CLI per action
```

Current packages:

- **`Packages/acronyms`** — maintains `Acronyms/acronyms.md`. Actions: `link` (wikilink defined acronyms), `add` (insert new entry or park in Pending), `detect` (scan for undefined ALL-CAPS), `triage` (walk Pending).
- **`Packages/orphans`** — vault link hygiene. Actions: `categorize` (the canonical pass — supersedes `Scripts/categorize_orphans.py` in the vault), `deadends` (notes with no outgoing links), `promote` (Categories-only candidates), `trend` (per-run count log).

## Common commands

Python 3.10+, standard library only. Dry-run by default; `--apply` writes to the vault.

```bash
# Acronyms
python Packages/acronyms/scripts/link_acronyms.py
python Packages/acronyms/scripts/link_acronyms.py --apply
python Packages/acronyms/scripts/add_acronym.py --term API --definition "Application Programming Interface"
python Packages/acronyms/scripts/detect_acronyms.py --top 30

# Orphans
python Packages/orphans/scripts/categorize.py
python Packages/orphans/scripts/categorize.py --apply
python Packages/orphans/scripts/deadends.py --top 50
python Packages/orphans/scripts/promote.py --by-category
python Packages/orphans/scripts/trend.py
python Packages/orphans/scripts/trend.py --show
```

No test suite yet. Verify behavior by previewing against the real vault before `--apply`.

## Conventions (not enforced by tooling)

These hold across packages. Diverging silently is the failure mode to watch for.

1. **Vault path resolution.** Every script accepts `--vault PATH`; falls back to the `COWORK_VAULT` env var; defaults to `/mnt/d/Dropbox/Vault`. The acronyms and orphans packages also accept the legacy `VAULT` env var that the original vault-side scripts used.
2. **Dry-run default.** Anything that mutates the vault must require an explicit `--apply` flag. The dry-run output should show exactly what would change.
3. **Idempotency.** Running a mutation twice should be a no-op the second time.
4. **Append-only.** Scripts add lines; they don't reorder, rewrite, or delete content. The user owns deletion. Frontmatter `created:` is preserved across runs; only `updated:` is bumped.
5. **Supersede, don't fork.** When a CoWork package replaces a vault-side script, document the migration in the package README. The user retires the vault script manually — the bash sandbox can't `rm` or `mv` inside the FUSE-mounted vault, so deletion goes through the Obsidian CLI from PowerShell (see `D:\Dropbox\Vault\CLAUDE.md` § "Available Tooling: Obsidian CLI").
6. **Hard rules belong in SKILL.md.** When a vault convention has hard rules (alphabetical sort, hyphen-not-em-dash, exclusion model, category resolution priority), encode them in the package's SKILL.md so any agent invoking the skill enforces them automatically. The scripts mechanically enforce; the skill explains why.
7. **`Research/` is local-only.** Gitignored. Surveys, scratch notes, and exploratory findings live there. Don't reference Research/ files from package code or SKILL.md — they may not exist on another clone.

## Architecture — "vault is substrate, CoWork is verb"

The vault is the durable Markdown content; CoWork is the executable tooling that operates on it. The tools live in CoWork (versioned, testable, sharable) so the vault stays plain-text-only and readable from any Obsidian client.

A package typically has one umbrella skill (`skills/<name>/SKILL.md`) with action-dispatch in the body, plus one Python CLI per action. The skill body encodes the *rules* (what's allowed, what order matters, what's forbidden); the scripts encode the *mechanism*. Both layers reference the same source of truth, so they don't drift.

Package boundaries are by **vault concern**, not by code-reuse. `acronyms` and `orphans` both read frontmatter and parse Markdown, but they don't share a library because they're maintained independently and have different lifecycles. If a third package ends up needing the same low-level utility, that's the right time to extract a shared `Packages/_lib/` — not before.

## Owner / context

- GitHub: `Dexatron-LLC/CoWork` (public)
- Maintainer: Dexter J. Le Blanc Jr. (`dexter@dexatron.com`)
- Local working directory: `/mnt/d/Source/AI/cowork` (WSL view of `D:\Source\AI\cowork`)
- Vault: `/mnt/d/Dropbox/Vault` (WSL) / `D:\Dropbox\Vault` (Windows)
