from contextlib import contextmanager
from unittest.mock import patch

from tools.skill_manager_tool import _create_skill, _edit_skill


VALID_SKILL_CONTENT = """---
name: my-skill
description: Test skill.
---

# My Skill
"""


@contextmanager
def _skill_dir(tmp_path):
    with patch("tools.skill_manager_tool.SKILLS_DIR", tmp_path), \
         patch("agent.skill_utils.get_all_skills_dirs", return_value=[tmp_path]):
        yield


def test_create_skill_syncs_vault_projection(tmp_path):
    with _skill_dir(tmp_path), patch("agent.vault_projection.sync_skills_projection") as mock_sync:
        result = _create_skill("my-skill", VALID_SKILL_CONTENT)

    assert result["success"] is True
    mock_sync.assert_called_once()


def test_edit_skill_syncs_vault_projection(tmp_path):
    updated = "---\nname: my-skill\ndescription: Updated.\n---\n\n# Updated\n"
    with _skill_dir(tmp_path):
        _create_skill("my-skill", VALID_SKILL_CONTENT)
        with patch("agent.vault_projection.sync_skills_projection") as mock_sync:
            result = _edit_skill("my-skill", updated)

    assert result["success"] is True
    mock_sync.assert_called_once()
