# Maintenance-Stage Extractor Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a deterministic extractor that stages repeated people, projects, concepts, weakly linked session notes, and duplicate-looking notes into the Obsidian maintenance surfaces.

**Architecture:** Extend `agent/vault_projection.py` with a conservative maintenance-sync helper that reads existing projected session notes, aggregates repeated candidate entities using explicit deterministic rules, and writes only to staging notes such as `nexus/maintenance/inbox/YYYY-MM-DD.md`, `nexus/maintenance/merge-candidates.md`, and `nexus/maintenance/orphans.md`. Do not create canonical people/project/concept notes yet.

**Tech Stack:** Python, pytest, file-backed vault projection helpers, existing session-note corpus under `nexus/sessions/`.

---

### Task 1: Add failing tests for maintenance extraction
**Objective:** Define the staging outputs before implementation.

**Files:**
- Modify: `tests/agent/test_vault_projection.py`

**Step 1:** Add a test that creates a tiny vault session corpus with repeated references and asserts the maintenance sync writes:
- candidate people section
- candidate projects section
- candidate concepts section
- candidate links with full-path wikilinks
- merge-candidates note
- orphans note

**Step 2:** Run the targeted test and verify failure.

Run: `pytest tests/agent/test_vault_projection.py -q`
Expected: FAIL — maintenance extractor missing.

### Task 2: Implement deterministic maintenance extractor
**Objective:** Build the smallest truthful extractor that stages repeated evidence without pretending to do semantic understanding.

**Files:**
- Modify: `agent/vault_projection.py`
- Test: `tests/agent/test_vault_projection.py`

**Step 1:** Add helpers to iterate session notes.
**Step 2:** Add deterministic candidate extraction rules for known people/projects/concepts.
**Step 3:** Add helper to detect orphan session notes with no curated links.
**Step 4:** Add helper to detect merge candidates based on duplicate/near-duplicate titles.
**Step 5:** Add a public sync function that writes:
- `nexus/maintenance/inbox/YYYY-MM-DD.md`
- `nexus/maintenance/merge-candidates.md`
- `nexus/maintenance/orphans.md`

**Step 6:** Re-run tests.

Run: `pytest tests/agent/test_vault_projection.py -q`
Expected: PASS.

### Task 3: Add a real backfill driver invocation
**Objective:** Make it easy to run against the current vault corpus now.

**Files:**
- Modify: `docs/plans/2026-04-16-maintenance-stage-extractor.md` only if needed for command notes

**Step 1:** Run the helper directly from a one-off Python command with explicit `HERMES_HOME` and `OBSIDIAN_VAULT_PATH`.
**Step 2:** Read back the written notes with file tools.

### Task 4: Regression verification
**Objective:** Prove the extractor works and does not break existing vault projection behaviors.

**Files:**
- Test only

**Step 1:** Run:
`pytest tests/agent/test_vault_projection.py tests/run_agent/test_vault_projection_hooks.py tests/tools/test_skill_manager_vault_projection.py tests/cron/test_jobs_vault_projection.py -q`

**Step 2:** Perform a live vault smoke run and verify the maintenance notes changed as expected.
