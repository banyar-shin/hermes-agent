# Vault Projection Phase 1 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add deterministic Obsidian vault mirrors for memory, session finalization, skills, and cron jobs.

**Architecture:** Add a small internal `agent/vault_projection.py` helper that no-ops unless `OBSIDIAN_VAULT_PATH` is set. Wire explicit call sites in `run_agent.py`, `tools/skill_manager_tool.py`, and `cron/jobs.py`, and cover behavior with focused unit tests.

**Tech Stack:** Python, pytest, file-backed mirrors, existing `HERMES_HOME`/skills/session abstractions.

---

### Task 1: Add failing tests for the projection helper
**Objective:** Define the exact mirror outputs before implementation.

**Files:**
- Create: `tests/agent/test_vault_projection.py`
- Modify: none

**Step 1:** Write tests for memory mirror + changelog, session note generation, skills index sync, and cron mirror sync.

**Step 2:** Run targeted tests.

Run: `pytest tests/agent/test_vault_projection.py -q`
Expected: FAIL — module/function missing.

### Task 2: Add the projection helper
**Objective:** Implement deterministic file writers with env-gated no-op behavior.

**Files:**
- Create: `agent/vault_projection.py`
- Test: `tests/agent/test_vault_projection.py`

**Step 1:** Implement vault path resolution and safe write helpers.
**Step 2:** Implement memory mirror + changelog sync.
**Step 3:** Implement session note writer.
**Step 4:** Implement skills index sync.
**Step 5:** Implement cron jobs mirror sync.

**Step 6:** Run helper tests.

Run: `pytest tests/agent/test_vault_projection.py -q`
Expected: PASS.

### Task 3: Wire memory + session hooks
**Objective:** Trigger projection from real session boundaries.

**Files:**
- Modify: `run_agent.py`
- Create/Modify: `tests/run_agent/test_vault_projection_hooks.py`

**Step 1:** Write failing tests asserting memory writes call the projection helper and session finalization syncs a note.
**Step 2:** Run tests to verify failure.
**Step 3:** Add minimal hook calls in `run_agent.py`.
**Step 4:** Re-run tests.

Run: `pytest tests/run_agent/test_vault_projection_hooks.py -q`
Expected: PASS.

### Task 4: Wire skill + cron hooks
**Objective:** Keep skill and cron mirror notes current after mutations.

**Files:**
- Modify: `tools/skill_manager_tool.py`
- Modify: `cron/jobs.py`
- Create/Modify: `tests/tools/test_skill_manager_vault_projection.py`
- Create/Modify: `tests/cron/test_jobs_vault_projection.py`

**Step 1:** Write failing tests asserting successful skill mutations sync the skills index and job mutations sync cron mirror notes.
**Step 2:** Run tests to verify failure.
**Step 3:** Add minimal hook calls on successful mutations.
**Step 4:** Re-run tests.

Run: `pytest tests/tools/test_skill_manager_vault_projection.py tests/cron/test_jobs_vault_projection.py -q`
Expected: PASS.

### Task 5: Regression verification
**Objective:** Prove the feature works without breaking nearby systems.

**Files:**
- Test only

**Step 1:** Run all targeted tests.

Run: `pytest tests/agent/test_vault_projection.py tests/run_agent/test_vault_projection_hooks.py tests/tools/test_skill_manager_vault_projection.py tests/cron/test_jobs_vault_projection.py tests/agent/test_memory_provider.py tests/tools/test_skill_manager_tool.py tests/cron/test_cron_script.py -q`
Expected: PASS.
