# cowork-acronyms

A CoWork package for maintaining the vault's `Acronyms/acronyms.md` glossary.

## What it does

Four actions, all dispatched from the `acronyms` skill:

- **`link`** — wikilink defined acronyms across the vault. Idempotent; skips frontmatter, code, existing links, URLs.
- **`add`** — insert a new entry (or park in Pending) respecting alphabetical order, hyphen format, excluded categories, and the frontmatter `updated:` bump.
- **`detect`** — scan vault Markdown for ALL-CAPS tokens not yet in the glossary, sorted by frequency.
- **`triage`** — interactive walk of the Pending section.

The hard rules are encoded in the skill body (`skills/acronyms/SKILL.md`) and enforced by the scripts.

## Layout

```
.claude-plugin/plugin.json     # plugin manifest
skills/acronyms/SKILL.md       # the umbrella skill (rules + dispatch)
scripts/
    glossary.py                # parser/writer for acronyms.md
    link_acronyms.py           # link CLI
    add_acronym.py             # add CLI
    detect_acronyms.py         # detect CLI
```

## Vault path

All scripts default to `/mnt/d/Dropbox/Vault`. Override per-call with `--vault PATH` or globally with the `COWORK_VAULT` environment variable.

## CLI usage (without the skill)

```bash
cd Packages/acronyms

# Preview link pass
python scripts/link_acronyms.py

# Apply link pass
python scripts/link_acronyms.py --apply

# Add a defined acronym
python scripts/add_acronym.py --term API --definition "Application Programming Interface"

# Park unknown
python scripts/add_acronym.py --pending DON --note "Embertide notification design"

# Detect undefined tokens (>=2 occurrences, top 50)
python scripts/detect_acronyms.py
```

## Why this lives in CoWork, not the vault

The vault is the substrate (Markdown content + rules). CoWork is the verb layer (executable tooling that operates on the vault). Keeping the scripts here means:

- The vault stays plain-text and tool-free; anyone with Obsidian alone can read it.
- The scripts get versioned alongside the rest of the CoWork agentic tooling.
- Multiple Claude Code sessions (or scheduled tasks) can invoke the same code path.

## Requirements

- Python 3.10+ (uses `dataclass` + structural pattern matching idioms compatible with 3.10).
- No third-party dependencies. Standard library only.
