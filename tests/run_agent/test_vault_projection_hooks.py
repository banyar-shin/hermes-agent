from unittest.mock import MagicMock, patch

from run_agent import AIAgent


@patch("tools.memory_tool.memory_tool")
def test_invoke_tool_memory_syncs_vault_projection(mock_memory_tool):
    agent = AIAgent.__new__(AIAgent)
    agent._memory_store = object()
    agent._memory_manager = None
    agent.session_id = "sess-1"

    mock_memory_tool.return_value = '{"success": true}'

    with patch("agent.vault_projection.sync_memory_projection") as mock_sync:
        result = agent._invoke_tool(
            "memory",
            {
                "action": "add",
                "target": "user",
                "content": "Prefers concise responses",
            },
            effective_task_id="task-1",
        )

    assert result == '{"success": true}'
    mock_sync.assert_called_once_with(
        action="add",
        target="user",
        content="Prefers concise responses",
        session_id="sess-1",
    )


def test_shutdown_memory_provider_projects_session_from_db_when_messages_missing():
    agent = AIAgent.__new__(AIAgent)
    agent._memory_manager = None
    agent.context_compressor = None
    agent.session_id = "sess-2"
    agent._session_db = MagicMock()
    agent._session_db.get_messages.return_value = [{"role": "user", "content": "hello vault"}]
    agent._session_db.get_session.return_value = {"source": "discord", "title": "Thread title"}

    with patch("agent.vault_projection.write_session_projection") as mock_write:
        agent.shutdown_memory_provider(messages=None)

    mock_write.assert_called_once_with(
        session_id="sess-2",
        messages=[{"role": "user", "content": "hello vault"}],
        session_meta={"source": "discord", "title": "Thread title"},
    )


def test_shutdown_memory_provider_refreshes_maintenance_projection_after_session_write():
    agent = AIAgent.__new__(AIAgent)
    agent._memory_manager = None
    agent.context_compressor = None
    agent.session_id = "sess-3"
    agent._session_db = MagicMock()
    agent._session_db.get_messages.return_value = [{"role": "user", "content": "hello maintenance"}]
    agent._session_db.get_session.return_value = {"source": "discord", "title": "Maintenance thread"}

    with patch("agent.vault_projection.write_session_projection") as mock_write, patch(
        "agent.vault_projection.sync_maintenance_stage_projection"
    ) as mock_maintenance:
        agent.shutdown_memory_provider(messages=None)

    mock_write.assert_called_once()
    mock_maintenance.assert_called_once_with()
