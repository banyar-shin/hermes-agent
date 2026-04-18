from pathlib import Path

from tools.memory_tool import ENTRY_DELIMITER


def _write_memory_file(path: Path, entries: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if entries:
        path.write_text(ENTRY_DELIMITER.join(entries), encoding="utf-8")
    else:
        path.write_text("", encoding="utf-8")


def test_sync_memory_projection_writes_mirror_and_changelog(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))

    _write_memory_file(
        tmp_path / ".hermes" / "memories" / "USER.md",
        ["Prefers concise responses", "Calls the assistant Nexus"],
    )

    from agent import vault_projection as vp

    written = vp.sync_memory_projection(
        action="add",
        target="user",
        content="Prefers concise responses",
        session_id="sess-123",
    )

    assert written is True

    mirror = (tmp_path / "vault" / "nexus" / "memory" / "user-profile.md").read_text(encoding="utf-8")
    changelog = (tmp_path / "vault" / "nexus" / "memory" / "changelog.md").read_text(encoding="utf-8")

    assert "# User Profile Mirror" in mirror
    assert "Prefers concise responses" in mirror
    assert "Calls the assistant Nexus" in mirror
    assert "action: add" in changelog
    assert "target: user" in changelog
    assert "source_session: sess-123" in changelog


def test_write_session_projection_creates_deterministic_note(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))

    from agent import vault_projection as vp

    note_path = vp.write_session_projection(
        session_id="discord_abc123",
        messages=[
            {"role": "user", "content": "lets design a deterministic vault mirror"},
            {"role": "assistant", "content": "Here is the architecture."},
        ],
        session_meta={"source": "discord", "title": "Vault design"},
    )

    assert note_path is not None
    text = Path(note_path).read_text(encoding="utf-8")
    assert "type: nexus-session" in text
    assert "session_id: discord_abc123" in text
    assert "source: discord" in text
    assert "Vault design" in text
    assert "lets design a deterministic vault mirror" in text
    assert "Open Loops" in text


def test_sync_skills_projection_indexes_custom_skills(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))

    skills_dir = tmp_path / "skills"
    skill_dir = skills_dir / "devops" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Test skill.\n---\n\n# My Skill\n",
        encoding="utf-8",
    )

    from agent import vault_projection as vp

    index_path = vp.sync_skills_projection(skill_dirs=[skills_dir])
    assert index_path is not None
    text = Path(index_path).read_text(encoding="utf-8")
    assert "# Nexus Skill Index" in text
    assert "my-skill" in text
    assert "Test skill." in text
    assert "devops" in text


def test_sync_cron_projection_writes_job_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))

    from agent import vault_projection as vp

    index_path = vp.sync_cron_projection(
        jobs=[
            {
                "id": "job123",
                "name": "daily digest",
                "schedule_display": "0 8 * * *",
                "deliver": "discord",
                "skills": ["discord-news-digest"],
                "script": "scripts/digest.py",
                "enabled": True,
                "state": "scheduled",
            }
        ]
    )

    assert index_path is not None
    text = Path(index_path).read_text(encoding="utf-8")
    assert "# Cron Jobs Mirror" in text
    assert "job123" in text
    assert "daily digest" in text
    assert "discord-news-digest" in text
    assert "scripts/digest.py" in text


def test_sync_maintenance_stage_projection_writes_staging_notes(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))

    vault = tmp_path / "vault"
    sessions_dir = vault / "nexus" / "sessions" / "2026"
    sessions_dir.mkdir(parents=True)

    (sessions_dir / "2026-04-16-session-a.md").write_text(
        """---
id: session-a
type: nexus-session
date: 2026-04-16
session_id: a
source: discord
title: Build second brain mirrors
message_count: 2
---

# Session Projection

## Summary
- Title: Build second brain mirrors
- First user message: Banrawr wants Nexus to build the second-brain projection for hermes-agent using Obsidian and tmux.
- Last assistant message: Claude and Codex can help with the Nexus control plane.

## Curated links
- [[nexus/ops/nexus-vault-brain-spec]]
- [[knowledge/maps/current-focus]]
""",
        encoding="utf-8",
    )
    (sessions_dir / "2026-04-16-session-b.md").write_text(
        """---
id: session-b
type: nexus-session
date: 2026-04-16
session_id: b
source: cli
title: Extend second brain maintenance
message_count: 2
---

# Session Projection

## Summary
- Title: Extend second brain maintenance
- First user message: Banrawr wants Nexus to add maintenance staging for the second-brain vault and hermes-agent runtime.
- Last assistant message: Claude should review the Obsidian maintenance flow.
""",
        encoding="utf-8",
    )

    from agent import vault_projection as vp

    inbox_path = vp.sync_maintenance_stage_projection(date_str="2026-04-16")

    assert inbox_path is not None
    inbox_text = (vault / "nexus" / "maintenance" / "inbox" / "2026-04-16.md").read_text(encoding="utf-8")
    merge_text = (vault / "nexus" / "maintenance" / "merge-candidates.md").read_text(encoding="utf-8")
    orphan_text = (vault / "nexus" / "maintenance" / "orphans.md").read_text(encoding="utf-8")

    assert "## Candidate people" in inbox_text
    assert "Banrawr" in inbox_text
    assert "Nexus" in inbox_text
    assert "## Candidate projects" in inbox_text
    assert "second-brain" in inbox_text
    assert "hermes-agent" in inbox_text
    assert "## Candidate concepts" in inbox_text
    assert "maintenance staging" in inbox_text
    assert "[[nexus/sessions/2026/2026-04-16-session-a]]" in inbox_text
    assert "[[nexus/sessions/2026/2026-04-16-session-b]]" in inbox_text
    assert "needs more links" in orphan_text
    assert "2026-04-16-session-b" in orphan_text
    assert "potential overlap" in merge_text
    assert "second brain" in merge_text.lower()


def test_projection_noops_without_vault_path(tmp_path, monkeypatch):
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))

    from agent import vault_projection as vp

    assert vp.sync_memory_projection(action="add", target="user", content="x") is False
    assert vp.write_session_projection(session_id="s1", messages=[]) is None
    assert vp.sync_skills_projection(skill_dirs=[]) is None
    assert vp.sync_cron_projection(jobs=[]) is None
    assert vp.sync_maintenance_stage_projection(date_str="2026-04-16") is None
