from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

from agent.skill_utils import get_all_skills_dirs, parse_frontmatter
from hermes_time import now as _hermes_now
from tools.memory_tool import get_memory_dir


VAULT_ENV_VAR = "OBSIDIAN_VAULT_PATH"


def get_obsidian_vault_path() -> Optional[Path]:
    raw = os.getenv(VAULT_ENV_VAR, "").strip()
    if not raw:
        return None
    return Path(os.path.expanduser(os.path.expandvars(raw))).resolve()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_text(path: Path, content: str) -> Path:
    _ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    return path


def _append_text(path: Path, content: str) -> Path:
    _ensure_parent(path)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _read_memory_entries(target: str) -> list[str]:
    filename = "USER.md" if target == "user" else "MEMORY.md"
    path = get_memory_dir() / filename
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return [part.strip() for part in text.split("\n§\n") if part.strip()]


def _render_bullets(entries: Iterable[str]) -> str:
    items = [e.strip() for e in entries if str(e).strip()]
    if not items:
        return "- _No entries mirrored yet._"
    return "\n".join(f"- {item.replace(chr(10), chr(10) + '  ')}" for item in items)


def sync_memory_projection(
    action: str,
    target: str,
    content: str,
    *,
    session_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    vault_path: Optional[Path] = None,
) -> bool:
    vault = vault_path or get_obsidian_vault_path()
    if vault is None:
        return False

    now = timestamp or _hermes_now()
    entries = _read_memory_entries(target)
    note_name = "user-profile.md" if target == "user" else "agent-notes.md"
    title = "User Profile Mirror" if target == "user" else "Agent Notes Mirror"
    source_name = "USER.md" if target == "user" else "MEMORY.md"

    mirror_body = (
        f"---\n"
        f"type: nexus-memory-mirror\n"
        f"source: {source_name}\n"
        f"last_synced: {now.isoformat()}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"Auto-generated deterministic mirror of `{source_name}`.\n\n"
        f"## Mirrored entries\n"
        f"{_render_bullets(entries)}\n"
    )
    _write_text(vault / "nexus" / "memory" / note_name, mirror_body)

    changelog = (
        f"\n## {now.isoformat()}\n"
        f"- action: {action}\n"
        f"- target: {target}\n"
        f"- content: {content.strip() or '_empty_'}\n"
        f"- source_session: {session_id or 'unknown'}\n"
    )
    changelog_path = vault / "nexus" / "memory" / "changelog.md"
    if not changelog_path.exists():
        _write_text(
            changelog_path,
            "---\ntype: nexus-memory-changelog\n---\n\n# Memory Changelog\n",
        )
    _append_text(changelog_path, changelog)
    return True


def _slug_session(session_id: str) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "-" for ch in session_id).strip("-")
    return clean or "session"


def _extract_user_seed(messages: list[dict[str, Any]]) -> str:
    for msg in messages:
        if msg.get("role") == "user" and str(msg.get("content") or "").strip():
            return str(msg.get("content")).strip()
    return ""


def _extract_assistant_seed(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and str(msg.get("content") or "").strip():
            return str(msg.get("content")).strip()
    return ""


def write_session_projection(
    *,
    session_id: str,
    messages: list[dict[str, Any]],
    session_meta: Optional[dict[str, Any]] = None,
    vault_path: Optional[Path] = None,
    timestamp: Optional[datetime] = None,
) -> Optional[str]:
    vault = vault_path or get_obsidian_vault_path()
    if vault is None:
        return None

    now = timestamp or _hermes_now()
    meta = session_meta or {}
    source = str(meta.get("source") or "unknown")
    title = str(meta.get("title") or "").strip()
    user_seed = _extract_user_seed(messages)
    assistant_seed = _extract_assistant_seed(messages)
    date_str = now.strftime("%Y-%m-%d")
    year = now.strftime("%Y")
    file_name = f"{date_str}-session-{_slug_session(session_id)[:32]}.md"
    note_path = vault / "nexus" / "sessions" / year / file_name

    content = (
        f"---\n"
        f"id: session-{_slug_session(session_id)}\n"
        f"type: nexus-session\n"
        f"date: {date_str}\n"
        f"session_id: {session_id}\n"
        f"source: {source}\n"
        f"title: {title or 'Untitled'}\n"
        f"message_count: {len(messages)}\n"
        f"---\n\n"
        f"# Session Projection\n\n"
        f"## Summary\n"
        f"- Title: {title or 'Untitled'}\n"
        f"- First user message: {user_seed or '_none_'}\n"
        f"- Last assistant message: {assistant_seed or '_none_'}\n\n"
        f"## Decisions\n- _Deterministic session projection does not infer decisions yet._\n\n"
        f"## Open Loops\n- _None extracted deterministically._\n\n"
        f"## Source\n- Session ID: `{session_id}`\n- Source: `{source}`\n"
    )
    _write_text(note_path, content)
    return str(note_path)


def _iter_skill_dirs(skill_dirs: Optional[list[Path]] = None) -> list[Path]:
    if skill_dirs is not None:
        return [Path(p) for p in skill_dirs]
    return get_all_skills_dirs()


def sync_skills_projection(*, skill_dirs: Optional[list[Path]] = None, vault_path: Optional[Path] = None) -> Optional[str]:
    vault = vault_path or get_obsidian_vault_path()
    if vault is None:
        return None

    rows: list[str] = []
    for base_dir in _iter_skill_dirs(skill_dirs):
        if not base_dir.exists():
            continue
        for skill_md in sorted(base_dir.rglob("SKILL.md")):
            rel = skill_md.relative_to(base_dir)
            if len(rel.parts) < 2:
                continue
            skill_name = rel.parts[-2]
            category = rel.parts[-3] if len(rel.parts) >= 3 else "uncategorized"
            frontmatter, _body = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            description = str(frontmatter.get("description") or "").strip()
            rows.append(
                f"- `{skill_name}` — {description or 'No description.'} "
                f"(category: `{category}`, path: `{rel.parent}`)"
            )

    body = "\n".join(rows) if rows else "- _No skills mirrored._"
    path = vault / "nexus" / "skills" / "index.md"
    content = (
        f"---\ntype: nexus-skill-index\nlast_synced: {_hermes_now().isoformat()}\n---\n\n"
        f"# Nexus Skill Index\n\n"
        f"{body}\n"
    )
    _write_text(path, content)
    return str(path)


def sync_cron_projection(*, jobs: list[dict[str, Any]], vault_path: Optional[Path] = None) -> Optional[str]:
    vault = vault_path or get_obsidian_vault_path()
    if vault is None:
        return None

    rows: list[str] = []
    for job in jobs:
        skills = job.get("skills") or ([] if not job.get("skill") else [job.get("skill")])
        rows.append(
            "- "
            f"`{job.get('id', '?')}` — {job.get('name', 'Unnamed job')} "
            f"| schedule: `{job.get('schedule_display') or job.get('schedule', {}).get('display', 'unknown')}` "
            f"| deliver: `{job.get('deliver', 'local')}` "
            f"| skills: `{', '.join(skills) if skills else 'none'}` "
            f"| script: `{job.get('script') or 'none'}` "
            f"| state: `{job.get('state') or ('scheduled' if job.get('enabled', True) else 'disabled')}`"
        )

    body = "\n".join(rows) if rows else "- _No cron jobs mirrored._"
    path = vault / "nexus" / "ops" / "cron-jobs.md"
    content = (
        f"---\ntype: nexus-cron-registry\nlast_synced: {_hermes_now().isoformat()}\n---\n\n"
        f"# Cron Jobs Mirror\n\n"
        f"{body}\n"
    )
    _write_text(path, content)
    return str(path)


_PEOPLE_PATTERNS: dict[str, tuple[str, ...]] = {
    "Banrawr": (r"\bbanrawr\b",),
    "Nexus": (r"\bnexus\b",),
    "Claude": (r"\bclaude\b",),
    "Codex": (r"\bcodex\b",),
    "Chrono": (r"\bchrono\b",),
    "Hermes": (r"\bhermes\b",),
    "Terr": (r"\bterr\b",),
    "Mnemo": (r"\bmnemo\b",),
}

_PROJECT_PATTERNS: dict[str, tuple[str, ...]] = {
    "second-brain": (r"\bsecond[- ]brain\b",),
    "hermes-agent": (r"\bhermes-agent\b",),
    "Obsidian": (r"\bobsidian\b",),
    "tmux": (r"\btmux\b",),
    "Discord control plane": (r"\bdiscord control plane\b", r"\bcontrol plane\b"),
}

_CONCEPT_PATTERNS: dict[str, tuple[str, ...]] = {
    "maintenance staging": (r"\bmaintenance staging\b",),
    "truthful mirrors": (r"\btruthful mirrors\b",),
    "vault projection": (r"\bvault projection\b", r"\bprojection layer\b"),
    "deterministic mirrors": (r"\bdeterministic mirrors\b", r"\bdeterministic mirror\b"),
}

_TITLE_STOPWORDS = {
    "a", "an", "and", "the", "for", "to", "of", "in", "on", "with", "from",
    "build", "extend", "add", "using", "use", "into",
}


def _session_note_link(path: Path, vault: Path) -> str:
    return f"[[{path.relative_to(vault).with_suffix('').as_posix()}]]"


def _scan_pattern_table(text: str, table: dict[str, tuple[str, ...]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label, patterns in table.items():
        total = 0
        for pattern in patterns:
            total += len(re.findall(pattern, text, flags=re.IGNORECASE))
        if total > 0:
            counts[label] = total
    return counts


def _load_session_notes(vault: Path) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    sessions_root = vault / "nexus" / "sessions"
    if not sessions_root.exists():
        return notes

    for note_path in sorted(sessions_root.rglob("*.md")):
        if note_path.name in {"index.md", "sessions.md"}:
            continue
        text = note_path.read_text(encoding="utf-8")
        frontmatter, _body = parse_frontmatter(text)
        notes.append(
            {
                "path": note_path,
                "text": text,
                "title": str(frontmatter.get("title") or note_path.stem),
                "source": str(frontmatter.get("source") or "unknown"),
                "date": str(frontmatter.get("date") or "unknown"),
            }
        )
    return notes


def _collect_candidates(notes: list[dict[str, Any]], vault: Path, table: dict[str, tuple[str, ...]]) -> dict[str, list[str]]:
    aggregated: dict[str, list[str]] = {}
    for note in notes:
        matches = _scan_pattern_table(note["text"], table)
        if not matches:
            continue
        link = _session_note_link(note["path"], vault)
        for label in sorted(matches):
            aggregated.setdefault(label, []).append(link)
    return aggregated


def _render_candidate_section(title: str, candidates: dict[str, list[str]]) -> str:
    lines = [f"## {title}"]
    if not candidates:
        lines.append("- _None staged._")
        return "\n".join(lines)
    ordered = sorted(candidates.items(), key=lambda item: (-len(dict.fromkeys(item[1])), item[0]))
    for label, links in ordered:
        unique_links = sorted(dict.fromkeys(links))
        preview = unique_links[:8]
        remaining = len(unique_links) - len(preview)
        suffix = f" (+{remaining} more)" if remaining > 0 else ""
        lines.append(
            f"- **{label}** — {len(unique_links)} session note(s). Examples: {', '.join(preview)}{suffix}"
        )
    return "\n".join(lines)


def _collect_orphans(notes: list[dict[str, Any]], vault: Path) -> list[str]:
    rows: list[str] = []
    for note in notes:
        if "## Curated links" in note["text"]:
            continue
        rows.append(f"- needs more links: {_session_note_link(note['path'], vault)}")
    return rows


def _title_tokens(title: str) -> set[str]:
    tokens = {tok for tok in re.findall(r"[a-z0-9]+", title.lower()) if tok not in _TITLE_STOPWORDS}
    return {tok for tok in tokens if len(tok) >= 2}


def _collect_merge_candidates(notes: list[dict[str, Any]], vault: Path) -> list[str]:
    rows: list[str] = []
    for idx, left in enumerate(notes):
        left_tokens = _title_tokens(left["title"])
        if not left_tokens:
            continue
        for right in notes[idx + 1:]:
            right_tokens = _title_tokens(right["title"])
            overlap_set = left_tokens & right_tokens
            if len(overlap_set) < 2:
                continue
            ordered_overlap = [
                tok for tok in re.findall(r"[a-z0-9]+", left["title"].lower())
                if tok in overlap_set and tok not in _TITLE_STOPWORDS
            ]
            rows.append(
                "- potential overlap: "
                f"{_session_note_link(left['path'], vault)} <-> {_session_note_link(right['path'], vault)} "
                f"| shared phrase: `{' '.join(ordered_overlap)}` "
                f"| shared title tokens: `{', '.join(ordered_overlap)}`"
            )
    return rows


def sync_maintenance_stage_projection(*, date_str: Optional[str] = None, vault_path: Optional[Path] = None) -> Optional[str]:
    vault = vault_path or get_obsidian_vault_path()
    if vault is None:
        return None

    now = _hermes_now()
    effective_date = date_str or now.strftime("%Y-%m-%d")
    notes = _load_session_notes(vault)

    people = _collect_candidates(notes, vault, _PEOPLE_PATTERNS)
    projects = _collect_candidates(notes, vault, _PROJECT_PATTERNS)
    concepts = _collect_candidates(notes, vault, _CONCEPT_PATTERNS)
    orphan_rows = _collect_orphans(notes, vault)
    merge_rows = _collect_merge_candidates(notes, vault)
    orphan_preview = orphan_rows[:50]
    orphan_remaining = len(orphan_rows) - len(orphan_preview)

    inbox_path = vault / "nexus" / "maintenance" / "inbox" / f"{effective_date}.md"
    candidate_links = []
    for label, links in list(people.items())[:2] + list(projects.items())[:2]:
        if links:
            candidate_links.append(f"- **{label}** -> {links[0]}")
    inbox = (
        f"---\n"
        f"type: nexus-maintenance-inbox\n"
        f"date: {effective_date}\n"
        f"status: staged\n"
        f"source_window: session corpus backfill\n"
        f"review_state: needs-human-review\n"
        f"last_synced: {now.isoformat()}\n"
        f"---\n\n"
        f"# Maintenance Inbox — {effective_date}\n\n"
        f"Deterministic staging output derived from projected session notes.\n\n"
        f"{_render_candidate_section('Candidate people', people)}\n\n"
        f"{_render_candidate_section('Candidate projects', projects)}\n\n"
        f"{_render_candidate_section('Candidate concepts', concepts)}\n\n"
        f"## Candidate links\n"
        f"{chr(10).join(candidate_links) if candidate_links else '- _None staged._'}\n\n"
        f"## Deferred\n"
        f"- Do not create canonical people/project/concept notes automatically from this staging output.\n"
        f"- Review ambiguous candidates manually before promotion.\n\n"
        f"## Provenance\n"
        f"- session note count: {len(notes)}\n"
        f"- session index: [[nexus/sessions/index]]\n"
        f"- merge candidates: [[nexus/maintenance/merge-candidates]]\n"
        f"- orphans: [[nexus/maintenance/orphans]]\n"
    )
    _write_text(inbox_path, inbox)

    merge_path = vault / "nexus" / "maintenance" / "merge-candidates.md"
    merge_text = (
        f"---\n"
        f"type: nexus-merge-candidates\n"
        f"last_synced: {now.isoformat()}\n"
        f"---\n\n"
        f"# Merge Candidates\n\n"
        f"{chr(10).join(merge_rows) if merge_rows else '- _None staged._'}\n"
    )
    _write_text(merge_path, merge_text)

    orphan_path = vault / "nexus" / "maintenance" / "orphans.md"
    orphan_text = (
        f"---\n"
        f"type: nexus-orphans\n"
        f"last_synced: {now.isoformat()}\n"
        f"---\n\n"
        f"# Orphans\n\n"
        f"- total weakly linked notes: {len(orphan_rows)}\n"
        f"{chr(10).join(orphan_preview) if orphan_preview else '- _None staged._'}\n"
        f"{'- ... truncated for readability.' if orphan_remaining > 0 else ''}\n"
    )
    _write_text(orphan_path, orphan_text)

    return str(inbox_path)
