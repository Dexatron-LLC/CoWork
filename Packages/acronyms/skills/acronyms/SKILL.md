---
name: acronyms
description: Use when the user asks to add, link, detect, or triage acronyms in the vault Acronyms glossary, or whenever the user introduces a new ALL-CAPS term in vault content that may need a glossary entry. Triggers on phrases like "add an acronym", "link acronyms", "scan the vault for new acronyms", "what's in Pending", "promote a Pending entry", or any edit to `Acronyms/acronyms.md`. Encodes the glossary's hard rules (hyphen-not-em-dash, alphabetical sort, excluded categories) and dispatches to the four scripts in `scripts/`.
argument-hint: <action: link | add | detect | triage> [...action args]
allowed-tools: Bash, Read, Edit, Write
---

# acronyms — vault glossary maintenance

Maintain `Acronyms/acronyms.md` (the vault's single canonical glossary) and keep its wikilinks current across the vault. The user's vault is at `D:\Dropbox\Vault` (WSL: `/mnt/d/Dropbox/Vault`); override with `--vault PATH` or the `COWORK_VAULT` env var.

## Hard rules (non-negotiable)

These come from the vault's `CLAUDE.md` and the glossary file itself. Violating them causes downstream tooling to break.

1. **Format:** `- **ACRONYM** - Full definition (optional context)`. The separator is a hyphen-space-space (`** - `), **never** an em-dash. Em-dashes are forbidden vault-wide.
2. **Sort:** alphabetical within each `## A` ... `## Z` letter section. Insertion must respect sort order; never append blindly.
3. **Excluded categories** (do **not** add as entries):
    - LinkedIn `#LI-` tracking codes (e.g. `#LI-Remote`, `#LI-Hybrid`)
    - Unit symbols (KB, MB, GB, TB, MHz, GHz, Hz)
    - Date/version/priority markers (Q1, Q4, P1, P2, P3, v1, v2)
    - Generic English initialisms (USA, US, UK, OK, FAQ, ASAP, FYI, RSVP)
4. **Frontmatter:** bump the `updated:` field to today's date on every change.
5. **Unknown definitions:** park in the `## Pending / [needs definition]` section at the bottom — never guess.
6. **Wikilink form:** `[[Acronyms/acronyms#<first-letter>|<TERM>]]`, e.g. `[[Acronyms/acronyms#A|API]]`. The anchor letter must match the term's first character.
7. **Multiple meanings:** semicolon-separate on one line, OR sub-bullets if disambiguation is non-trivial. Both forms exist in the file; pick the one that reads cleanest.

## Action dispatch

Parse the first argument as the action. Each action calls a script in this plugin's `scripts/` directory. Always run the dry-run/preview form first; only re-run with `--apply` after the user confirms.

### `link` — wikilink defined acronyms across the vault

Run the linker pass. Idempotent: skips frontmatter, fenced/inline code, existing wikilinks, markdown links, raw URLs, and the glossary file itself. Only matches whole-word ALL-CAPS tokens.

```bash
# Preview
python ${CLAUDE_PLUGIN_ROOT}/scripts/link_acronyms.py
# Apply
python ${CLAUDE_PLUGIN_ROOT}/scripts/link_acronyms.py --apply
```

Useful flags: `--include 'Job_Search/**'` to scope to a folder; `--exclude '_archive/**'` to skip one. Both repeatable.

### `add` — insert a new entry

Use when the user introduces a new acronym in vault content, OR explicitly asks to add one. If the definition is known, use `--term/--definition`; otherwise park it in Pending.

```bash
# Known definition
python ${CLAUDE_PLUGIN_ROOT}/scripts/add_acronym.py --term API --definition "Application Programming Interface"
# Unknown — park for later
python ${CLAUDE_PLUGIN_ROOT}/scripts/add_acronym.py --pending DON --note "appears in Embertide notification design; possibly Department of the Navy"
```

The script handles alphabetical insertion, the `updated:` bump, and excluded-category enforcement. It refuses to clobber an existing entry.

After adding one or more entries with definitions, **always** offer to follow up with `link` so the new term gets wikilinked across the vault.

### `detect` — scan for undefined ALL-CAPS tokens

Use when the user asks "what acronyms are missing", "scan the vault", or after a large batch of new content has been added. Defaults to tokens appearing 2+ times.

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/detect_acronyms.py --top 50
# With file context
python ${CLAUDE_PLUGIN_ROOT}/scripts/detect_acronyms.py --top 30 --show-files
# Tighter threshold
python ${CLAUDE_PLUGIN_ROOT}/scripts/detect_acronyms.py --min-count 5
```

For each surfaced token, decide between three outcomes (in this order):

1. **Excluded category match** → don't add (the script already filters obvious cases, but check borderline ones).
2. **Definition known** → call the `add` action with `--term/--definition`.
3. **Definition unknown** → call the `add` action with `--pending` and a `--note` citing where you saw it.

### `triage` — walk the Pending section

Use when the user asks to triage Pending, promote unresolved entries, or as a periodic cleanup pass.

The Pending section lives at the bottom of `acronyms.md` after the `## Z` section. There is no script for triage — it is interactive by nature.

Procedure:

1. Read `acronyms.md` and locate `## Pending / [needs definition]`.
2. For each entry, look up the cited context (the note in parentheses tells you which file to grep). Use Bash + grep to find the actual usages.
3. Propose one of: **promote** (you found a definition; call `add --term/--definition` then remove the Pending line), **keep pending** (still unclear), or **drop** (it was a false positive — likely an excluded-category case the detector missed).
4. After all triage decisions, write the cleaned Pending section back via Edit on the glossary file directly. Bump the `updated:` field.
5. Offer to run `link` if any entries were promoted.

## When triggered without an explicit action

If the user just says "add API" or pastes a definition, infer:

- One acronym + definition → `add --term/--definition`.
- An ALL-CAPS token mentioned in vault content with no definition → check `has_term` in the glossary first; only escalate to `add --pending` if absent.
- A request to "update / refresh / re-link the glossary" → `link` (preview then apply).
- A request to "audit / find missing / what's not defined" → `detect`.

## Common pitfalls

- **Em-dash creep.** Some editors auto-correct ` - ` to ` — `. Visually inspect the diff before committing changes to the glossary; the `add` script writes a hyphen but a manual Edit can slip.
- **Wrong letter section.** The wikilink anchor `#<letter>` must match the entry's actual letter section. Numbers and symbols don't get their own section in this glossary.
- **Pending-section duplication.** A term can drift into `## A` *and* `## Pending` if added carelessly. The `add` script's `has_term` check covers both, but a manual Edit can desync them.
- **FUSE mount blocks `mv` and `unlink` inside the vault.** This plugin only writes (`Path.write_text`), which works fine through the FUSE layer. If a script ever needs to delete or rename a file in the vault, drive the Obsidian CLI from PowerShell instead — see vault `CLAUDE.md` for the pattern.
- **Don't re-link inside the glossary file.** The linker excludes `Acronyms/` by default; if you change the include/exclude flags, keep that exclusion.

## Verifying behaviour

After any mutation, surface a one-line confirmation including: action, term(s) touched, file(s) written, frontmatter date. The dry-run / `--apply` split is the primary safety net — never `--apply` without a preview unless the user explicitly says "go".
