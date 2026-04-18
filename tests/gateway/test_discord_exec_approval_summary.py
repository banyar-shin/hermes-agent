from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import sys

import pytest

from gateway.config import PlatformConfig


class FakeEmbed:
    def __init__(self, *, title=None, description=None, color=None):
        self.title = title
        self.description = description
        self.color = color
        self.fields = []

    def add_field(self, *, name, value, inline=False):
        self.fields.append(SimpleNamespace(name=name, value=value, inline=inline))


class FakeView:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def _ensure_discord_mock():
    if "discord" in sys.modules and hasattr(sys.modules["discord"], "__file__"):
        return

    discord_mod = MagicMock()
    discord_mod.Intents.default.return_value = MagicMock()
    discord_mod.Client = MagicMock
    discord_mod.File = MagicMock
    discord_mod.DMChannel = type("DMChannel", (), {})
    discord_mod.Thread = type("Thread", (), {})
    discord_mod.ForumChannel = type("ForumChannel", (), {})
    discord_mod.ui = SimpleNamespace(View=FakeView, button=lambda *a, **k: (lambda fn: fn), Button=object)
    discord_mod.ButtonStyle = SimpleNamespace(success=1, primary=2, secondary=2, danger=3, green=1, grey=2, blurple=2, red=3)
    discord_mod.Color = SimpleNamespace(orange=lambda: 1, green=lambda: 2, blue=lambda: 3, red=lambda: 4, purple=lambda: 5)
    discord_mod.Interaction = object
    discord_mod.Embed = FakeEmbed
    discord_mod.app_commands = SimpleNamespace(
        describe=lambda **kwargs: (lambda fn: fn),
        choices=lambda **kwargs: (lambda fn: fn),
        Choice=lambda **kwargs: SimpleNamespace(**kwargs),
    )

    ext_mod = MagicMock()
    commands_mod = MagicMock()
    commands_mod.Bot = MagicMock
    ext_mod.commands = commands_mod

    sys.modules["discord"] = discord_mod
    sys.modules["discord.ext"] = ext_mod
    sys.modules["discord.ext.commands"] = commands_mod


_ensure_discord_mock()

from gateway.platforms.discord import DiscordAdapter, _build_exec_approval_summary  # noqa: E402


def test_build_exec_approval_summary_for_branch_switch_script():
    command = """set -euo pipefail
ROOT=/Users/banyar/git-repos/work/_ego/chat-app
for pane in ego:3.1 ego:3.2; do
  tmux respawn-pane -k -t \"$pane\" -c \"$ROOT\" \"bash -lc 'echo stopped for branch switch; exec ${SHELL:-/bin/bash} -l'\"
done
sleep 2
cd \"$ROOT\"
git fetch --all --prune
git branch backup/test main
git checkout team/shared-auth-embed-share
git reset --hard origin/team/shared-auth-embed-share
"""
    summary = _build_exec_approval_summary(command, "shell command via -c/-lc flag")

    assert "manage tmux panes/sessions" in summary
    assert "fetch remote git refs" in summary
    assert "switch git branches" in summary
    assert "hard-reset tracked files" in summary
    assert "team/shared-auth-embed-share" in summary


@pytest.mark.asyncio
async def test_send_exec_approval_includes_plain_english_summary_field():
    adapter = DiscordAdapter(PlatformConfig(enabled=True, token="***"))
    sent_msg = SimpleNamespace(id=1234)
    channel = SimpleNamespace(send=AsyncMock(return_value=sent_msg))
    adapter._client = SimpleNamespace(
        get_channel=lambda _chat_id: channel,
        fetch_channel=AsyncMock(),
    )

    result = await adapter.send_exec_approval(
        chat_id="555",
        command="git fetch --all --prune && git checkout team/shared-auth-embed-share && git reset --hard origin/team/shared-auth-embed-share",
        session_key="session-1",
        description="shell command via -c/-lc flag",
    )

    assert result.success is True
    embed = channel.send.await_args.kwargs["embed"]
    assert [field.name for field in embed.fields] == ["What this does", "Reason"]
    assert "fetch remote git refs" in embed.fields[0].value
    assert "switch git branches" in embed.fields[0].value
    assert "team/shared-auth-embed-share" in embed.fields[0].value
    assert embed.fields[1].value == "shell command via -c/-lc flag"
