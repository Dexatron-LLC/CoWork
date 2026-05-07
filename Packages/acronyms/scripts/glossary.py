"""Parser and writer for the vault's Acronyms/acronyms.md glossary.

The glossary is the single source of truth for vault-wide acronym definitions.
This module reads the file into a structured form, lets callers query and
mutate it, and writes it back preserving the file's conventions:

  - One entry per line: `- **ACRONYM** - definition`
  - Hyphen between term and definition (NOT em-dash)
  - Sorted alphabetically within each `## A` ... `## Z` letter section
  - A `## Pending / [needs definition]` section at the bottom
  - A `## Excluded categories` section that documents (in prose) what NOT
    to add to the glossary
  - YAML frontmatter with an `updated:` field that bumps on each change
"""

from __future__ import annotations

import datetime as _dt
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ENTRY_RE = re.compile(r"^- \*\*(?P<term>[^*]+)\*\* - (?P<definition>.+)$")
LETTER_HEADING_RE = re.compile(r"^## ([A-Z])\s*$")
SPECIAL_HEADING_RE = re.compile(r"^## (Pending.*|Excluded categories.*)$")
H1_RE = re.compile(r"^# .+$")


@dataclass
class Entry:
    term: str
    definition: str

    def render(self) -> str:
        return f"- **{self.term}** - {self.definition}"


@dataclass
class Glossary:
    """In-memory representation of acronyms.md."""

    path: Path
    frontmatter: list[str] = field(default_factory=list)
    preamble: list[str] = field(default_factory=list)
    sections: dict[str, list[Entry]] = field(default_factory=dict)
    pending_block: list[str] = field(default_factory=list)
    excluded_block: list[str] = field(default_factory=list)
    raw_text: str = ""

    @classmethod
    def load(cls, path: Path) -> "Glossary":
        text = path.read_text(encoding="utf-8")
        g = cls(path=path, raw_text=text)
        g._parse(text)
        return g

    def _parse(self, text: str) -> None:
        lines = text.splitlines()
        i = 0

        if lines and lines[0].strip() == "---":
            self.frontmatter.append(lines[0])
            i = 1
            while i < len(lines) and lines[i].strip() != "---":
                self.frontmatter.append(lines[i])
                i += 1
            if i < len(lines):
                self.frontmatter.append(lines[i])
                i += 1

        current_section: str | None = None
        in_pending = False
        in_excluded = False

        while i < len(lines):
            line = lines[i]
            letter_match = LETTER_HEADING_RE.match(line)
            special_match = SPECIAL_HEADING_RE.match(line)

            if letter_match:
                current_section = letter_match.group(1)
                in_pending = False
                in_excluded = False
                self.sections.setdefault(current_section, [])
                i += 1
                continue
            if special_match:
                heading_text = special_match.group(1).lower()
                in_pending = "pending" in heading_text
                in_excluded = "excluded" in heading_text
                current_section = None
                bucket = self.pending_block if in_pending else self.excluded_block
                bucket.append(line)
                i += 1
                continue

            if current_section is not None:
                m = ENTRY_RE.match(line)
                if m:
                    self.sections[current_section].append(
                        Entry(term=m.group("term").strip(), definition=m.group("definition").strip())
                    )
                # Drop blank/heading-adjacent lines silently — render rebuilds them.
            elif in_pending:
                self.pending_block.append(line)
            elif in_excluded:
                self.excluded_block.append(line)
            else:
                self.preamble.append(line)
            i += 1

    def has_term(self, term: str) -> bool:
        upper = term.upper()
        for entries in self.sections.values():
            if any(e.term.upper() == upper for e in entries):
                return True
        return self._term_in_pending(upper)

    def _term_in_pending(self, upper_term: str) -> bool:
        pat = re.compile(rf"\*\*{re.escape(upper_term)}\*\*")
        return any(pat.search(line) for line in self.pending_block)

    def all_terms(self) -> list[str]:
        return [e.term for entries in self.sections.values() for e in entries]

    def add_entry(self, term: str, definition: str) -> bool:
        """Insert a new entry into its letter section in alphabetical order.

        Returns True if added, False if the term already exists.
        """
        if self.has_term(term):
            return False
        letter = term[0].upper()
        if letter not in self.sections:
            self.sections[letter] = []
        bucket = self.sections[letter]
        new_entry = Entry(term=term, definition=definition)
        for idx, existing in enumerate(bucket):
            if existing.term.upper() > term.upper():
                bucket.insert(idx, new_entry)
                self._bump_updated()
                return True
        bucket.append(new_entry)
        self._bump_updated()
        return True

    def add_pending(self, term: str, note: str = "") -> bool:
        if self.has_term(term):
            return False
        suffix = f" - [needs definition]" if not note else f" - {note}"
        line = f"- **{term}**{suffix}"
        self.pending_block.append(line)
        self._bump_updated()
        return True

    def _bump_updated(self) -> None:
        today = _dt.date.today().isoformat()
        for idx, line in enumerate(self.frontmatter):
            if line.startswith("updated:"):
                self.frontmatter[idx] = f"updated: {today}"
                return

    def render(self) -> str:
        out: list[str] = []
        out.extend(self.frontmatter)
        out.extend(self.preamble)
        for letter in sorted(self.sections):
            out.append(f"## {letter}")
            out.append("")
            for e in self.sections[letter]:
                out.append(e.render())
            out.append("")
        if self.pending_block:
            out.append("---")
            out.append("")
            out.extend(self.pending_block)
            out.append("")
        if self.excluded_block:
            out.extend(self.excluded_block)
            if not out[-1].endswith("\n"):
                out.append("")
        text = "\n".join(out).rstrip() + "\n"
        return text

    def save(self) -> None:
        self.path.write_text(self.render(), encoding="utf-8")


def default_vault_path() -> Path:
    env = os.environ.get("COWORK_VAULT")
    if env:
        return Path(env)
    return Path("/mnt/d/Dropbox/Vault")


def glossary_path(vault: Path) -> Path:
    return vault / "Acronyms" / "acronyms.md"


_COMMON_CAPS_WORDS = {
    "AND", "BUT", "FOR", "NOT", "THE", "WITH", "FROM", "INTO", "ONTO", "OVER",
    "UNDER", "ABOVE", "BELOW", "BETWEEN", "WITHIN", "WITHOUT",
    "YES", "NO", "OFF", "ON", "OPEN", "CLOSED", "DONE", "TODO", "PASS", "FAIL",
    "NEW", "OLD", "ALL", "ANY", "NONE", "EACH", "EVERY", "MANY", "FEW",
    "WHEN", "WHERE", "WHY", "HOW", "WHAT", "WHO", "WHICH",
    "TRUE", "FALSE", "NULL",
    "ADD", "REMOVE", "DELETE", "UPDATE", "CREATE", "READ", "WRITE",
    "POSITIVE", "NEGATIVE", "PROFESSIONAL", "PERSONAL", "DEFAULT",
    "REQUIRED", "OPTIONAL", "ENABLED", "DISABLED",
    "SUMMARY", "OVERVIEW", "DETAILS", "EXAMPLE", "EXAMPLES", "NOTE", "NOTES",
    "WARNING", "ERROR", "INFO", "DEBUG",
}


def excluded_token(token: str) -> bool:
    """Heuristic for tokens that should NOT enter the glossary.

    Covers the file's documented excluded categories plus common English
    ALL-CAPS words that show up in vault prose (headings, emphasis, table
    cells) and would otherwise pollute detection output.
    """
    upper = token.upper()
    if token.startswith("LI-"):
        return True
    if upper in {"USA", "US", "UK", "OK", "FAQ", "ASAP", "FYI", "RSVP"}:
        return True
    if upper in _COMMON_CAPS_WORDS:
        return True
    if re.fullmatch(r"(KB|MB|GB|TB|PB|MHZ|GHZ|HZ)", upper):
        return True
    if re.fullmatch(r"(P|Q|V)\d+", upper):
        return True
    return False
