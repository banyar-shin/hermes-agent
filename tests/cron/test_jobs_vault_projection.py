import pytest


@pytest.fixture
def cron_env(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    (hermes_home / "cron").mkdir(parents=True)
    (hermes_home / "cron" / "output").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    import cron.jobs as jobs_mod

    monkeypatch.setattr(jobs_mod, "HERMES_DIR", hermes_home)
    monkeypatch.setattr(jobs_mod, "CRON_DIR", hermes_home / "cron")
    monkeypatch.setattr(jobs_mod, "JOBS_FILE", hermes_home / "cron" / "jobs.json")
    monkeypatch.setattr(jobs_mod, "OUTPUT_DIR", hermes_home / "cron" / "output")
    return jobs_mod


def test_create_job_syncs_vault_projection(cron_env):
    from unittest.mock import patch

    with patch("agent.vault_projection.sync_cron_projection") as mock_sync:
        job = cron_env.create_job(prompt="hello", schedule="every 1h")

    assert job["id"]
    mock_sync.assert_called_once()


def test_update_and_remove_job_sync_vault_projection(cron_env):
    from unittest.mock import patch

    job = cron_env.create_job(prompt="hello", schedule="every 1h")

    with patch("agent.vault_projection.sync_cron_projection") as mock_sync:
        updated = cron_env.update_job(job["id"], {"name": "renamed"})
    assert updated["name"] == "renamed"
    mock_sync.assert_called_once()

    with patch("agent.vault_projection.sync_cron_projection") as mock_sync:
        removed = cron_env.remove_job(job["id"])
    assert removed is True
    mock_sync.assert_called_once()
