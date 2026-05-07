---
name: orphans
description: Use when the user asks to find orphan files, categorize orphans, run the categorize-orphans pass, scan for deadend notes, promote a Categories-only entry into Wiki, log or review orphan-count trends, or anything related to vault link hygiene. Triggers on phrases like "find orphans", "categorize the vault", "what's not linked", "scan for deadends", "promote from Categories", "orphan trend". Supersedes the legacy vault-side `Scripts/categorize_orphans.py` script and the `/categorize-orphans` slash command.
argument-hint: <action: categorize | deadends | promote | trend> [...action args]
allowed-tools: Bash, Read, Edit, Write
---

# orphans — vault link hygiene

Find and remediate three kinds of vault link decay: **inbound-orphans** (files no one links *to*), **deadends** (Markdown notes that link *to nothing*), and **stuck-in-Categories** notes (files whose only inbound link is from `Categories/<X>.md` — auto-categorized but otherwise dead). Optionally log per-run counts so the user can watch the trajectory over time.

The vault is at `D:\Dropbox\Vault` (WSL: `/mnt/d/Dropbox/Vault`); override per-call with `--vault PATH` or globally with `COWORK_VAULT`.

## Hard rules (preserved from the vault-side implementation)

These come from the existing `/categorize-orphans` command spec and the original `Scripts/categorize_orphans.py`. Any port must keep them.

1. **Append-only.** The `categorize` action only adds bullets under `## Items` in `Categories/<X>.md`. It never deletes, never reorders, never overwrites note content. Frontmatter `created:` is preserved; only `updated:` is bumped.
2. **Idempotent.** Once a file is linked from a Category, it's no longer an orphan — running again is a no-op for it.
3. **Two-tier exclusion model.**
    - **Hard-excluded** (matched at any depth): `.obsidian`, `.claude`, `.superpowers`, `.git`, `node_modules`, `_archive`, `Archive`. Not scanned.
    - **Soft-excluded top-level only**: `Categories/`. Scanned for *outgoing* links so they un-orphan their targets, but never themselves treated as orphan candidates.
4. **Category resolution priority** (first match wins):
    1. Extension override (`.bat / .sh / .ps1 / .py` → `Scripts`).
    2. Folder rules (`Dxtr/products` → `Woodworking Products`, etc.; ~30 rules; more specific first).
    3. Frontmatter `category` (Title-cased).
    4. Frontmatter `area` mapped via `AREA_TITLES` (`health-fitness` → `Health & Fitness`).
    5. Frontmatter `type` (Title-cased).
    6. Vault-root fallback → `"Vault Root"`; otherwise top-level folder name Title-cased.
5. **Wikilink form details.**
    - `.md` files: drop suffix in link (`[[Wiki/note]]`).
    - Attachments and scripts: keep extension (`[[Scripts/run.py]]`, `[[images/x.png]]`).
    - Path contains literal `#`: drop wikilink, use angle-bracket Markdown link `- [Display](<path/with#/file>)`.
6. **Obsidian-style link resolution.** Case-insensitive (NTFS-friendly). Extensionless refs resolve to `.md` only. Stem-uniqueness fallback when the full path doesn't match. Heading anchors split off the rightmost `#` only when the segment after has no slash (so `Senior Application Developer-C#/note` stays intact).

## Action dispatch

Parse the first argument as the action. Each action is a separate script in this plugin's `scripts/` directory. Always preview before applying.

### `categorize` — the canonical pass (writes to vault)

Walks the vault, identifies files with zero incoming links, computes each one's category, and ensures a bullet exists in `Categories/<Cat>.md`. This is the action that supersedes `Scripts/categorize_orphans.py`.

```bash
# Preview
python ${CLAUDE_PLUGIN_ROOT}/scripts/categorize.py
# Apply
python ${CLAUDE_PLUGIN_ROOT}/scripts/categorize.py --apply
```

After a successful `--apply`, mention the count of new categories created vs. items appended vs. duplicates skipped. Offer to log a trend sample (`trend` action) so the user can see whether the vault is accruing or shedding orphans over time.

### `deadends` — find notes with no outgoing links (read-only)

Complement of `categorize`. Returns Markdown notes whose body resolves to *zero* outbound references — a reader landing there has no way out. Read-only; never writes.

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/deadends.py
# Top 50 only
python ${CLAUDE_PLUGIN_ROOT}/scripts/deadends.py --top 50
# Include Categories/ files (normally excluded)
python ${CLAUDE_PLUGIN_ROOT}/scripts/deadends.py --include-categories
```

For each result, propose one of: **link it** (add a wikilink to a related Wiki note or MOC; preferred), **promote its content** (its standalone state suggests a Wiki entry hasn't absorbed the idea yet), or **archive** (it's done its job, move to `_archive/` via Obsidian CLI). Don't propose deletion casually — the user's archives are intentional history.

### `promote` — surface "Categories-only" notes (read-only)

Find files whose *only* inbound link is from a `Categories/<X>.md` file and nothing else. These were technically un-orphaned by the categorize pass but never thought about by the user. Most useful as part of a periodic review.

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/promote.py
# Group by category
python ${CLAUDE_PLUGIN_ROOT}/scripts/promote.py --by-category
# Add stems for quick identification
python ${CLAUDE_PLUGIN_ROOT}/scripts/promote.py --by-category --show-stem
```

For a candidate the user wants to promote: write or extend a Wiki note that references it (or add a wikilink from a relevant MOC), then optionally edit the bullet out of the Categories file once the real link exists.

### `trend` — log per-run orphan/deadend counts

Single-line history of the vault's link-hygiene state over time. Each invocation appends to a JSONL file in `~/.local/share/cowork-orphans/trend.jsonl` (override with `--state-dir` or `COWORK_ORPHANS_STATE`).

```bash
# Sample now
python ${CLAUDE_PLUGIN_ROOT}/scripts/trend.py
# Show recent history
python ${CLAUDE_PLUGIN_ROOT}/scripts/trend.py --show
# Last 10 samples
python ${CLAUDE_PLUGIN_ROOT}/scripts/trend.py --show --last 10
```

Useful as a once-a-week pulse during the weekly review. If the orphan count is climbing, the categorize pass isn't being run often enough OR the user is creating notes faster than they can integrate them — both are signals.

## When triggered without an explicit action

- "Find orphans" / "what's unlinked" → `categorize` in dry-run mode (no writes; just the report).
- "Run the orphan pass" / "categorize the vault" → `categorize --apply`.
- "What notes are dead-ends" / "scan for deadends" → `deadends`.
- "What notes are stuck in Categories" / "promote from Categories" → `promote --by-category`.
- "How are we doing on orphans" / "trend" → `trend --show`.
- An ambiguous request → `categorize` dry-run, then offer the others.

## Migration note (from vault-side script)

This plugin is the canonical implementation. The vault's `Scripts/categorize_orphans.py` is **superseded** and should be retired. Steps the user should take when ready:

1. Confirm `categorize.py --apply` produces the same result as the vault script for one or two test runs.
2. Delete `D:\Dropbox\Vault\Scripts\categorize_orphans.py` (FUSE blocks `rm` from the bash sandbox — drive the Obsidian CLI from PowerShell).
3. Update `D:\Dropbox\Vault\.claude\commands\categorize-orphans.md` to point to this skill instead of the local script (or delete it if the skill replaces it entirely).
4. Update `D:\Dropbox\Vault\CLAUDE.md` lines around the Categories section that reference `Scripts/categorize_orphans.py`.

Do **not** perform any of these vault-side deletions until the user explicitly confirms parity.

## Common pitfalls

- **Running `categorize` against the CoWork repo by mistake.** The default vault path is `/mnt/d/Dropbox/Vault`. If the user's `COWORK_VAULT` env var points elsewhere or they pass `--vault .`, the script will happily scan whatever directory it's given. Sanity-check by reading the first lines of output (it prints the vault path).
- **`Categories/Templates.md` confusion.** `Templates/` is not in the soft-exclude list, so template files with no callers are treated as orphans. That may or may not be intended; flag to the user on first run.
- **Don't auto-promote.** The `promote` action lists candidates; it does not modify the vault. Promotion to Wiki is a thinking step that requires the user.
- **Deadends in stub notes.** A new note with no links yet is technically a deadend, but it's also work-in-progress. Don't suggest archiving anything created in the last few days unless the user asks.

## Verifying behaviour

After any mutating action (`categorize --apply`):

- Surface counts: orphans found, categories created, items appended, duplicates skipped.
- Echo back the vault path that was scanned.
- Recommend a `trend` sample if one hasn't been logged today.

For read-only actions, surface counts only — no writes to confirm.
