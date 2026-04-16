from __future__ import annotations

import os
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
