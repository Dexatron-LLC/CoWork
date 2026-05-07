# CoWork

Executable tooling for an Obsidian vault. CoWork is the **verb layer** that operates on a Markdown-and-frontmatter vault — maintaining an acronym glossary, finding orphans, scanning for link rot — while the vault itself stays plain text and readable from any Obsidian client.

The design rule: keep the substrate (Markdown content) tool-free, and put all the executable logic in versioned Python packages. Each package is one vault concern.

## Packages

- **[acronyms](Packages/acronyms)** — vault-wide acronym glossary. Wikilinks defined terms across the vault, inserts new entries in alphabetical order, detects undefined ALL-CAPS tokens, and triages a Pending section.
- **[orphans](Packages/orphans)** — vault link hygiene. Categorizes files with no inbound links, surfaces deadend notes (no outbound links), identifies "Categories-only" candidates worth promoting, and logs per-run counts for trend analysis. Supersedes the legacy `Scripts/categorize_orphans.py` in the vault.

## Quick start

Every script is dry-run by default; pass `--apply` to write to the vault.

```bash
git clone https://github.com/Dexatron-LLC/CoWork.git
cd CoWork

# Preview what the orphans pass would do
python Packages/orphans/scripts/categorize.py

# Preview the acronym linker
python Packages/acronyms/scripts/link_acronyms.py
```

Vault path resolution: each script accepts `--vault PATH`; falls back to the `COWORK_VAULT` environment variable; defaults to `/mnt/d/Dropbox/Vault`.

## Layout

Monorepo. Each package is self-contained under `Packages/<name>/`:

```
Packages/<name>/
├── .claude-plugin/plugin.json   # Claude Code plugin manifest
├── README.md                    # package usage
├── skills/<name>/SKILL.md       # encodes hard rules and dispatches actions
└── scripts/
    ├── lib.py                   # shared utilities (when >1 script needs them)
    └── <action>.py              # one CLI per action
```

The `CLAUDE.md` at the repo root is the contract a Claude Code session reads at the start of each session. It's the index; substantive per-package rules live in each package's `SKILL.md`.

## Requirements

- Python 3.10+, standard library only (no third-party dependencies).
- An Obsidian vault structured along the conventions encoded in each package's `SKILL.md`. The packages are tightly coupled to one specific vault's folder shape and frontmatter schema; this is not a generic toolkit.

## Claude Code integration

Each package is a Claude Code plugin. The `SKILL.md` files surface as skills any Claude Code session can invoke ("find orphans in the vault", "add an acronym definition"), with the rules encoded so that an agent invoking the skill enforces them automatically. The Python scripts also work standalone from the command line — no Claude Code required to run them.

## Status

Two packages, shaped to a single contract: `Packages/<name>/` with a manifest, README, skill, and scripts. New capabilities land as new packages, not as additions to existing ones.

## Author

Dexter J. Le Blanc Jr. — [Dexatron LLC](https://github.com/Dexatron-LLC). Built for personal vault maintenance.
