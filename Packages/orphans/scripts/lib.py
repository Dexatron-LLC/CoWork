"""Shared library for the orphans package.

Factored out of the vault's Scripts/categorize_orphans.py so the canonical
categorize pass and the new capabilities (deadends, promote, trend) can
share one implementation of:

  - vault detection
  - file walking with the two-tier exclusion model
  - frontmatter parsing
  - Obsidian-style wikilink/embed/markdown-link parsing AND resolution
  - inbound and outbound link maps
  - category resolution (6-level priority)
  - category file rendering and idempotent upsert

Mirrors Obsidian's wikilink resolution rules: case-insensitive,
stem-uniqueness fallback, anchor handling, literal `#` in folder names.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote


# ---------- Vault detection ----------


def default_vault() -> Path:
    env = os.environ.get("COWORK_VAULT") or os.environ.get("VAULT")
    if env:
        return Path(env).resolve()
    return Path("/mnt/d/Dropbox/Vault")


# ---------- Exclusions ----------


HARD_EXCLUDED: frozenset[str] = frozenset(
    {
        ".obsidian",
        ".claude",
        ".superpowers",
        ".git",
        "node_modules",
        "_archive",
        "Archive",
    }
)

SOFT_EXCLUDED_TOPLEVEL: frozenset[str] = frozenset({"Categories"})


def is_hard_excluded(rel_path: Path) -> bool:
    return bool(set(rel_path.parts) & HARD_EXCLUDED)


def is_orphan_candidate(rel_path: Path) -> bool:
    if set(rel_path.parts) & HARD_EXCLUDED:
        return False
    if rel_path.parts and rel_path.parts[0] in SOFT_EXCLUDED_TOPLEVEL:
        return False
    return True


# ---------- Category configuration ----------


EXT_OVERRIDES: dict[str, str] = {
    ".bat": "Scripts",
    ".sh": "Scripts",
    ".ps1": "Scripts",
    ".py": "Scripts",
}


FOLDER_RULES: list[tuple[str, str]] = [
    ("Dxtr/products", "Woodworking Products"),
    ("Dxtr/customers", "Woodworking Customers"),
    ("Dxtr/finances", "Woodworking Finances"),
    ("Dxtr/sops", "Woodworking SOPs"),
    ("Dxtr/goals", "Woodworking Goals"),
    ("Dxtr/images", "Woodworking Images"),
    ("Dxtr", "Woodworking"),
    ("Dexatron/Canasta-score-pro", "Canasta Score Pro"),
    ("Dexatron", "Dexatron"),
    ("Job_Search/Applications", "Job Applications"),
    ("Job_Search/InBox", "Job Notifications"),
    ("Job_Search/research", "Job Search Research"),
    ("Job_Search/agents", "Job Search Agents"),
    ("Job_Search/commands", "Job Search Commands"),
    ("Job_Search/auto_search", "Job Search Automation"),
    ("Job_Search", "Job Search"),
    ("Projects/embertide", "Embertide"),
    ("Projects/SafePlate", "SafePlate"),
    ("Projects/Boat", "Boat Project"),
    ("Projects/canasta", "Canasta Score Pro"),
    ("Projects", "Projects"),
    ("Wiki", "Wiki Notes"),
    ("Research", "Research Reports"),
    ("Inbox", "Inbox Capture"),
    ("Acronyms", "Acronyms"),
    ("Docs", "Documentation"),
    ("Tools", "Tools"),
    ("Ideas", "Ideas"),
    ("logs", "Session Logs"),
    ("Reviews", "Reviews"),
    ("Habits", "Habits"),
    ("Tasks", "Tasks"),
    ("Scripts", "Scripts"),
    ("Templates", "Templates"),
    ("Private/goals", "Private Goals"),
    ("Private/Journal", "Journal"),
    ("Private", "Private"),
]


AREA_TITLES: dict[str, str] = {
    "career": "Career",
    "health-fitness": "Health & Fitness",
    "finance": "Finance",
    "learning": "Learning",
    "relationships": "Relationships",
    "woodworking": "Woodworking",
    "dexatron": "Dexatron",
    "creative-side-projects": "Creative Side Projects",
}


# ---------- Markdown patterns ----------


WIKILINK = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")
EMBED = re.compile(r"!\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")
MD_LINK_ANY = re.compile(
    r"!?\[[^\]]*\]\("
    r"(?:<([^>]+\.[a-zA-Z0-9]+)>"
    r"|([^)\s]+\.[a-zA-Z0-9]+))"
    r"\)"
)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
FRONTMATTER_FIELD = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", re.MULTILINE)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    body = m.group(1)
    out: dict[str, str] = {}
    for fm in FRONTMATTER_FIELD.finditer(body):
        key = fm.group(1)
        val = fm.group(2).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        out[key] = val
    return out


def get_h1(text: str) -> str | None:
    body_start = 0
    m = FRONTMATTER_RE.match(text)
    if m:
        body_start = m.end()
    body = text[body_start:]
    h1 = H1_RE.search(body)
    if h1:
        title = h1.group(1)
        title = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", title)
        title = re.sub(r"\[\[([^\]]+)\]\]", r"\1", title)
        return title.strip()
    return None


# ---------- File walking ----------


def all_link_source_files(vault: Path) -> list[Path]:
    """All .md files whose outgoing links count for orphan detection."""
    out: list[Path] = []
    for p in vault.rglob("*.md"):
        rel = p.relative_to(vault)
        if is_hard_excluded(rel):
            continue
        out.append(p)
    return out


def all_tracked_files(vault: Path) -> list[Path]:
    """Every regular file under non-hard-excluded paths."""
    out: list[Path] = []
    for p in vault.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(vault)
        if is_hard_excluded(rel):
            continue
        out.append(p)
    return out


# ---------- Link extraction and resolution ----------


def extract_refs(text: str) -> set[str]:
    """All outgoing references in a Markdown source: wikilinks, embeds,
    and Markdown links to files with extensions."""
    refs: set[str] = set()
    for m in WIKILINK.finditer(text):
        refs.add(m.group(1).strip())
    for m in EMBED.finditer(text):
        refs.add(m.group(1).strip())
    for m in MD_LINK_ANY.finditer(text):
        captured = m.group(1) or m.group(2)
        if not captured:
            continue
        captured = captured.strip().replace("\\", "/")
        if m.group(1) is None:
            captured = unquote(captured)
        refs.add(captured)
    return refs


def _last_segment_has_known_ext(ref: str) -> bool:
    last = ref.split("/")[-1]
    if "." not in last:
        return False
    ext = last.rsplit(".", 1)[1]
    return len(ext) <= 5 and ext.isalnum()


@dataclass
class _ResolveIndex:
    by_full_path: dict[str, Path]
    by_stripped_md: dict[str, Path]
    by_stem_md: dict[str, list[Path]]
    by_stem_all: dict[str, list[Path]]


def _build_resolve_index(vault: Path, targets: list[Path]) -> _ResolveIndex:
    by_full_path: dict[str, Path] = {}
    by_stripped_md: dict[str, Path] = {}
    by_stem_md: dict[str, list[Path]] = defaultdict(list)
    by_stem_all: dict[str, list[Path]] = defaultdict(list)
    for p in targets:
        rel = p.relative_to(vault)
        full = rel.as_posix().lower()
        by_full_path[full] = rel
        if p.suffix.lower() == ".md":
            by_stripped_md[rel.with_suffix("").as_posix().lower()] = rel
            by_stem_md[p.stem.lower()].append(rel)
        by_stem_all[p.stem.lower()].append(rel)
    return _ResolveIndex(by_full_path, by_stripped_md, by_stem_md, by_stem_all)


def resolve_link(ref: str, idx: _ResolveIndex) -> Path | None:
    """Mirror Obsidian's wikilink resolution (case-insensitive, anchors,
    stem-uniqueness fallback, literal `#` in folder names)."""
    ref = ref.strip()
    if not ref:
        return None
    ref_lc = ref.lower()

    if ref_lc in idx.by_full_path:
        return idx.by_full_path[ref_lc]

    has_ext = _last_segment_has_known_ext(ref)

    anchor_path = None
    if "#" in ref:
        path_part, anchor = ref.rsplit("#", 1)
        if "/" not in anchor and path_part:
            anchor_path = path_part.lower()

    if not has_ext:
        if ref_lc in idx.by_stripped_md:
            return idx.by_stripped_md[ref_lc]
        if ref_lc + ".md" in idx.by_full_path:
            return idx.by_full_path[ref_lc + ".md"]
        stem = Path(ref).stem.lower()
        cands = idx.by_stem_md.get(stem, [])
        if len(cands) == 1:
            return cands[0]
        if anchor_path is not None:
            if anchor_path in idx.by_stripped_md:
                return idx.by_stripped_md[anchor_path]
            if anchor_path + ".md" in idx.by_full_path:
                return idx.by_full_path[anchor_path + ".md"]
            anchor_stem = Path(anchor_path).stem
            cands = idx.by_stem_md.get(anchor_stem, [])
            if len(cands) == 1:
                return cands[0]
        return None

    if ref_lc in idx.by_full_path:
        return idx.by_full_path[ref_lc]
    stem = Path(ref).stem.lower()
    cands = idx.by_stem_all.get(stem, [])
    matching_ext = [c for c in cands if c.suffix.lower() == "." + ref.rsplit(".", 1)[1].lower()]
    if len(matching_ext) == 1:
        return matching_ext[0]
    return None


# ---------- Inbound and outbound link maps ----------


def build_link_maps(
    vault: Path, sources: list[Path], targets: list[Path]
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return (inbound, outbound).

    inbound[target_relpath] = {source_relpath, ...}  — who links TO target
    outbound[source_relpath] = {target_relpath, ...} — what target links FROM source resolve to
    """
    idx = _build_resolve_index(vault, targets)
    inbound: dict[str, set[str]] = defaultdict(set)
    outbound: dict[str, set[str]] = defaultdict(set)

    for src in sources:
        try:
            text = src.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, OSError):
            continue
        src_posix = src.relative_to(vault).as_posix()

        refs = extract_refs(text)
        for ref in refs:
            target_rel = resolve_link(ref, idx)
            if target_rel is None:
                continue
            target_posix = target_rel.as_posix()
            if target_posix == src_posix:
                continue
            inbound[target_posix].add(src_posix)
            outbound[src_posix].add(target_posix)

    return inbound, outbound


# ---------- Category resolution ----------


SLUG_TO_TITLE_RE = re.compile(r"[-_/]+")


def title_case(s: str) -> str:
    s = s.replace("&", "and")
    parts = SLUG_TO_TITLE_RE.split(s)
    out = " ".join(p[:1].upper() + p[1:] for p in parts if p)
    out = out.replace(" And ", " & ")
    return out


def category_for(vault: Path, path: Path, frontmatter: dict[str, str]) -> str:
    rel_path = path.relative_to(vault)
    rel = rel_path.as_posix()
    ext = path.suffix.lower()

    if ext in EXT_OVERRIDES:
        return EXT_OVERRIDES[ext]

    for prefix, name in FOLDER_RULES:
        if rel.startswith(prefix + "/") or rel == prefix:
            return name

    cat = frontmatter.get("category", "").strip()
    if cat:
        return title_case(cat)

    area = frontmatter.get("area", "").strip().strip("\"'")
    if area and area in AREA_TITLES:
        return AREA_TITLES[area]
    if area:
        return title_case(area)

    typ = frontmatter.get("type", "").strip().strip("\"'")
    if typ:
        return title_case(typ)

    if "/" not in rel:
        return "Vault Root"

    return title_case(rel_path.parts[0])


# ---------- Category file management ----------


def category_path(vault: Path, category: str) -> Path:
    safe = category.replace("/", "-")
    return vault / "Categories" / f"{safe}.md"


def category_template(category: str, today: str) -> str:
    return (
        "---\n"
        "type: category\n"
        f"name: {category}\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "tags: [category]\n"
        "---\n"
        "\n"
        f"# {category}\n"
        "\n"
        "Files in this category. Auto-managed by `cowork-orphans` (was `Scripts/categorize_orphans.py`).\n"
        "\n"
        "## Items\n"
        "\n"
    )


def link_for(vault: Path, orphan: Path, display: str | None) -> str:
    rel_full = orphan.relative_to(vault)
    if rel_full.suffix.lower() == ".md":
        rel = rel_full.with_suffix("").as_posix()
    else:
        rel = rel_full.as_posix()
    if "#" in rel:
        label = display or orphan.stem.replace("-", " ").replace("_", " ")
        return f"- [{label}](<{rel}>)"
    if display and display != orphan.stem:
        return f"- [[{rel}|{display}]]"
    return f"- [[{rel}]]"


def link_already_present(vault: Path, category_text: str, orphan: Path) -> bool:
    rel_full = orphan.relative_to(vault)
    if rel_full.suffix.lower() == ".md":
        rel = rel_full.with_suffix("").as_posix()
    else:
        rel = rel_full.as_posix()
    if "#" in rel:
        return f"](<{rel}>)" in category_text
    pat = re.compile(r"\[\[" + re.escape(rel) + r"(\||\]\])")
    return bool(pat.search(category_text))


def upsert_category(
    vault: Path,
    category: str,
    orphan: Path,
    display: str | None,
    *,
    apply: bool,
    today: str,
) -> str:
    """Returns 'created', 'appended', or 'skipped-duplicate'."""
    cat_path = category_path(vault, category)
    if cat_path.exists():
        text = cat_path.read_text(encoding="utf-8")
        if link_already_present(vault, text, orphan):
            return "skipped-duplicate"
        new_line = link_for(vault, orphan, display)
        if "## Items" in text:
            new_text = re.sub(
                r"(## Items\n\n(?:- .*\n)*)",
                lambda m: m.group(1) + new_line + "\n",
                text,
                count=1,
            )
        else:
            new_text = text.rstrip() + "\n\n## Items\n\n" + new_line + "\n"
        new_text = re.sub(r"^(updated:\s*).*$", r"\g<1>" + today, new_text, count=1, flags=re.MULTILINE)
        if apply:
            cat_path.write_text(new_text, encoding="utf-8")
        return "appended"
    new_line = link_for(vault, orphan, display)
    body = category_template(category, today) + new_line + "\n"
    if apply:
        cat_path.parent.mkdir(parents=True, exist_ok=True)
        cat_path.write_text(body, encoding="utf-8")
    return "created"


# ---------- Helpers for callers ----------


def today_iso() -> str:
    return _dt.date.today().isoformat()
