# CoWork

Executable tooling for an Obsidian vault. CoWork is the **verb layer** that operates on a Markdown-and-frontmatter vault — maintaining an acronym glossary, finding orphans, scanning for link rot — while the vault itself stays plain text and readable from any Obsidian client.

The design rule: keep the substrate (Markdown content) tool-free, and put all the executable logic in versioned Python packages. Each package is one vault concern.

## Packages

- **[acronyms](Packages/acronyms)** — vault-wide acronym glossary. Wikilinks defined terms across the vault, inserts new entries in alphabetical order, detects undefined ALL-CAPS tokens, and triages a Pending section.
- **[orphans](Packages/orphans)** — vault link hygiene. Categorizes files with no inbound links, surfaces deadend notes (no outbound links), identifies "Categories-only" candidates worth promoting, and logs per-run counts for trend analysis. Supersedes the legacy `Scripts/categorize_orphans.py` in the vault.

## Install

Each package is a [Claude Code](https://www.anthropic.com/claude-code) plugin and can also be run as a plain Python CLI. Three paths, in increasing order of friction:

### 1. Claude Code marketplace (recommended)

This repo is a Claude Code marketplace. From any Claude Code session:

```text
/plugin marketplace add Dexatron-LLC/CoWork
/plugin install acronyms@CoWork
/plugin install orphans@CoWork
```

The marketplace pulls from `main`; pushed changes are picked up on the next install.

### 2. One-off zip URL

For ad-hoc testing without registering a marketplace:

```bash
claude --plugin-url https://github.com/Dexatron-LLC/CoWork/releases/download/<tag>/orphans.zip
```

(Once a release is cut. Use `bin/build-zips.py` to produce the zips locally — see "Building distribution zips" below.)

### 3. Local clone for development

```bash
git clone https://github.com/Dexatron-LLC/CoWork.git
cd CoWork
claude --plugin-dir Packages/orphans
```

## Usage

Every script is dry-run by default; pass `--apply` to write to the vault.

```bash
# Preview what the orphans pass would do
python Packages/orphans/scripts/categorize.py

# Preview the acronym linker
python Packages/acronyms/scripts/link_acronyms.py

# Apply
python Packages/orphans/scripts/categorize.py --apply
```

Vault path resolution: each script accepts `--vault PATH`; falls back to the `COWORK_VAULT` environment variable; defaults to `/mnt/d/Dropbox/Vault`.

The Python scripts work standalone — no Claude Code required to run them. Inside a Claude Code session, the SKILL.md files surface as skills the agent invokes by intent ("find orphans in the vault", "add an acronym definition") with the package's hard rules encoded so the agent enforces them automatically.

## Layout

Monorepo. Each package is self-contained under `Packages/<name>/`:

```
Packages/<name>/
├── .claude-plugin/plugin.json   # plugin manifest
├── README.md                    # package usage
├── skills/<name>/SKILL.md       # encodes hard rules and dispatches actions
└── scripts/
    ├── lib.py                   # shared utilities (when >1 script needs them)
    └── <action>.py              # one CLI per action

.claude-plugin/marketplace.json  # repo-root marketplace listing both packages
bin/build-zips.py                # builds dist/<name>.zip for each package
```

The `CLAUDE.md` at the repo root is the contract a Claude Code session reads at the start of each session. It's the index; substantive per-package rules live in each package's `SKILL.md`.

## Building distribution zips

```bash
python bin/build-zips.py                   # zip every package -> dist/<name>.zip
python bin/build-zips.py --package orphans # one specific package
python bin/build-zips.py --clean           # rm dist/ first
```

Each archive is rooted at the package name (extracting `orphans.zip` yields a `orphans/` directory). Excludes `__pycache__` and `*.pyc`. Stdlib only. `dist/` is gitignored — attach the zips to a GitHub Release rather than committing them.

## Requirements

- Python 3.10+, standard library only (no third-party dependencies).
- An Obsidian vault structured along the conventions encoded in each package's `SKILL.md`. The packages are tightly coupled to one specific vault's folder shape and frontmatter schema; this is not a generic toolkit.

## Status

Two packages, shaped to a single contract: `Packages/<name>/` with a manifest, README, skill, and scripts. New capabilities land as new packages, not as additions to existing ones.

## Author

Dexter J. Le Blanc Jr. — [Dexatron LLC](https://github.com/Dexatron-LLC). Built for personal vault maintenance.
