# Brain Weekly Graph Population Implementation Plan

> **For Nexus:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a one-week pipeline that forms the Obsidian wiki from a local working copy, tracks progress with a deterministic coverage bar, runs nightly via cron, and syncs safely back to the iCloud vault.

**Architecture:** Add a local-vault workflow around the existing deterministic projection layer. Nightly maintenance should operate only on a local mirror of the vault, compute coverage metrics from the current note corpus, apply a conservative curated-link/promotion pass, write machine-readable and human-readable progress reports, then sync the changed files back to the iCloud vault. The progress bar must reflect real measurable coverage of the existing structure rather than a vague estimate.

**Tech Stack:** Python, pytest, existing `agent/vault_projection.py`, cron jobs, macOS local filesystem + `rsync`, Obsidian markdown notes, JSON metrics snapshots.

---

## Desired end-of-week outcome

By the end of the week, the user should have:
- a **local working copy** of the vault at a stable path, e.g. `/Users/banyar/.local/share/second-brain-local`
- a nightly job that:
  - syncs iCloud -> local
  - runs deterministic wiki formation on local
  - writes progress metrics + reports
  - syncs local -> iCloud
- a visible progress bar in:
  - `nexus/maintenance/reports/YYYY-MM-DD.md`
  - `nexus/maintenance/wiki-progress.md`
  - optional Discord delivery summary
- a more connected Obsidian graph following the current vault structure, not a newly invented taxonomy

## Progress model

Use a deterministic weighted score, capped at 100.

### Coverage dimensions

1. **Session curation coverage** — 40%
   - numerator: session notes containing `## Curated links`
   - denominator: total readable session notes under `nexus/sessions/**/*.md`

2. **Hub-link coverage** — 25%
   - numerator: readable session notes linking at least one canonical hub note
   - denominator: total readable session notes
   - canonical hubs initially:
     - `[[knowledge/maps/current-focus]]`
     - `[[knowledge/maps/banrawr-nexus-map]]`
     - `[[nexus/ops/nexus-vault-brain-spec]]`
     - `[[nexus/skills/index]]`
     - `[[nexus/ops/cron-jobs]]`

3. **Maintenance triage coverage** — 20%
   - numerator: staged orphan/merge candidates resolved or explicitly deferred with provenance
   - denominator: total staged candidates in `merge-candidates.md` + `orphans.md`

4. **Canonical promotion coverage** — 15%
   - numerator: promoted high-signal concepts/projects/relationships linked from a hub note
   - denominator: weekly target set (small and explicit, e.g. 8 promotions)

### Progress bar format

Store numeric metrics in JSON and render a bar in markdown.

Example:

```md
## Wiki coverage
- overall: `61%` `████████████░░░░░░`
- session curation: `72%`
- hub-link coverage: `44%`
- maintenance triage: `55%`
- canonical promotions: `38%`
```

### Truth constraints

- only count readable local notes
- never claim iCloud content was inspected if the run used metadata fallback
- do not count raw existence as curation
- do not count noisy links to over-common entities like `Nexus` alone as meaningful hub coverage

---

## Task 1: Create local vault workflow constants and helpers

**Objective:** Establish a deterministic local working-copy path and safe bidirectional sync helpers.

**Files:**
- Modify: `agent/vault_projection.py`
- Create: `tests/agent/test_vault_projection_local_sync.py`

**Step 1: Write failing tests**
- Add tests for:
  - default local vault path resolution
  - env override support (e.g. `OBSIDIAN_LOCAL_VAULT_PATH`)
  - safe no-op when source vault is missing
  - rsync command construction that excludes `.obsidian/workspace*.json`, transient locks, and trash files

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/agent/test_vault_projection_local_sync.py -q`
Expected: FAIL — helpers do not exist yet.

**Step 3: Add helpers**
- `get_local_obsidian_vault_path()`
- `sync_vault_to_local(...)`
- `sync_local_to_vault(...)`
- `ensure_local_vault_bootstrap(...)`

Use a stable default local path:
- `/Users/banyar/.local/share/second-brain-local`

Use `rsync -a --delete` with conservative excludes.

**Step 4: Re-run tests**

Run: `python -m pytest tests/agent/test_vault_projection_local_sync.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add agent/vault_projection.py tests/agent/test_vault_projection_local_sync.py
git commit -m "feat: add local vault sync helpers"
```

---

## Task 2: Add deterministic wiki coverage metrics

**Objective:** Compute measurable progress for the wiki-forming process.

**Files:**
- Modify: `agent/vault_projection.py`
- Create: `tests/agent/test_vault_projection_progress_metrics.py`

**Step 1: Write failing tests**
- Cover:
  - total/readable session counting
  - curated-link coverage percentage
  - hub-link coverage percentage
  - maintenance triage coverage percentage
  - canonical promotion coverage percentage
  - weighted overall score
  - markdown progress bar rendering

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/agent/test_vault_projection_progress_metrics.py -q`
Expected: FAIL — metrics helpers missing.

**Step 3: Implement helpers**
- `compute_wiki_coverage_metrics(vault_path: Path) -> dict`
- `render_progress_bar(percent: int, width: int = 20) -> str`
- `write_wiki_progress_reports(...)`

Write outputs to:
- `nexus/maintenance/wiki-progress.json`
- `nexus/maintenance/wiki-progress.md`

**Step 4: Re-run tests**

Run: `python -m pytest tests/agent/test_vault_projection_progress_metrics.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add agent/vault_projection.py tests/agent/test_vault_projection_progress_metrics.py
git commit -m "feat: add wiki coverage metrics and progress bars"
```

---

## Task 3: Add curated-link formation pass for session notes

**Objective:** Convert projected session notes into connected graph nodes without inventing semantics.

**Files:**
- Modify: `agent/vault_projection.py`
- Create: `tests/agent/test_vault_projection_curated_links.py`

**Step 1: Write failing tests**
- Verify session notes gain a `## Curated links` block when deterministic rules match
- Verify links use full-path wikilinks
- Verify duplicate links are deduped
- Verify over-common terms are suppressed or down-ranked

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/agent/test_vault_projection_curated_links.py -q`
Expected: FAIL.

**Step 3: Implement minimal curated-link pass**
- Add a helper like `sync_session_curated_links(...)`
- First link targets:
  - `[[knowledge/maps/current-focus]]`
  - `[[knowledge/maps/banrawr-nexus-map]]`
  - `[[nexus/ops/nexus-vault-brain-spec]]`
  - `[[nexus/ops/cron-jobs]]`
  - `[[nexus/skills/index]]`
- Only update a dedicated `## Curated links` section
- Preserve the rest of each note verbatim

**Step 4: Re-run tests**

Run: `python -m pytest tests/agent/test_vault_projection_curated_links.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add agent/vault_projection.py tests/agent/test_vault_projection_curated_links.py
git commit -m "feat: add deterministic curated-link sync for session notes"
```

---

## Task 4: Add canonical weekly promotion targets

**Objective:** Define the small set of notes that should become genuinely useful hubs this week.

**Files:**
- Modify: local vault notes under the local working copy
- Test: `tests/agent/test_vault_projection_progress_metrics.py` (update if needed)

**Initial promotion targets:**
1. `knowledge/maps/current-focus.md`
2. `knowledge/maps/banrawr-nexus-map.md`
3. `nexus/ops/nexus-vault-brain-spec.md`
4. `nexus/ops/cron-jobs.md`
5. `nexus/skills/index.md`
6. `me/relationships/nexus.md` (if missing, create in local vault)

**Step 1:** Create/update deterministic sections in those notes for backlinks / related threads.

**Step 2:** Make sure promoted notes are linked from maintenance outputs and session notes.

**Step 3:** Update the metrics target count for canonical promotions.

**Step 4:** Verify the local graph stays within the current structure.

**Step 5: Commit**

```bash
git add [updated note paths or code paths if note templates are generated]
git commit -m "feat: add canonical weekly graph promotion targets"
```

---

## Task 5: Add nightly local wiki-formation runner

**Objective:** Create one idempotent entrypoint for the nightly job.

**Files:**
- Create: `scripts/nightly_brain_formation.py`
- Create: `tests/scripts/test_nightly_brain_formation.py`

**Step 1: Write failing tests**
- Verify the runner calls, in order:
  - local sync bootstrap
  - iCloud -> local sync
  - deterministic mirror refreshes
  - curated-link sync
  - maintenance-stage sync
  - metrics/report write
  - local -> iCloud sync
- Verify failures emit partial status instead of silently aborting

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/scripts/test_nightly_brain_formation.py -q`
Expected: FAIL.

**Step 3: Implement runner**
The runner should:
1. resolve iCloud vault path + local vault path
2. emit a heartbeat/status dict after each phase
3. write:
   - `nexus/maintenance/reports/YYYY-MM-DD.md`
   - `nexus/maintenance/wiki-progress.json`
   - `nexus/maintenance/wiki-progress.md`
4. return machine-readable final status for cron delivery

**Step 4: Re-run tests**

Run: `python -m pytest tests/scripts/test_nightly_brain_formation.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/nightly_brain_formation.py tests/scripts/test_nightly_brain_formation.py
git commit -m "feat: add nightly brain formation runner"
```

---

## Task 6: Add heartbeat-style progress snapshots

**Objective:** Make nightly runs visibly trackable while they work.

**Files:**
- Modify: `scripts/nightly_brain_formation.py`
- Create: `tests/scripts/test_nightly_brain_formation_heartbeat.py`

**Step 1: Write failing tests**
- Verify the runner emits phase-by-phase status snapshots:
  - `bootstrap_local`
  - `sync_down`
  - `refresh_mirrors`
  - `curate_links`
  - `stage_maintenance`
  - `compute_progress`
  - `sync_up`
  - `complete`
- Verify heartbeat output can be summarized into markdown and cron delivery text

**Step 2:** Implement snapshot emission.

Write to:
- `nexus/maintenance/heartbeat/YYYY-MM-DD.json`

Optional markdown summary:
- `nexus/maintenance/heartbeat/YYYY-MM-DD.md`

**Step 3:** Re-run tests.

**Step 4: Commit**

```bash
git add scripts/nightly_brain_formation.py tests/scripts/test_nightly_brain_formation_heartbeat.py
git commit -m "feat: add nightly brain heartbeat snapshots"
```

---

## Task 7: Create the nightly cron job

**Objective:** Run the wiki-forming pipeline automatically each night.

**Files:**
- Modify: cron job registry via `cronjob` tool
- Optional support script: `~/.hermes/scripts/nightly_brain_formation_wrapper.py`

**Schedule recommendation:**
- `30 1 * * *` local time

**Delivery recommendation:**
- deliver back to the current Discord control channel or `nexus-out`

**Prompt behavior:**
- must be self-contained
- must not ask questions
- must report:
  - tonight's progress score
  - delta vs previous night
  - changed notes count
  - unresolved blockers

**Step 1:** Create a job named `weekly-brain-nightly-formation`

**Step 2:** Verify it appears in `nexus/ops/cron-jobs.md`

**Step 3:** Dry-run once manually.

**Step 4:** Confirm a report note + progress note are written.

---

## Task 8: Add local graph-friendly note updates

**Objective:** Ensure the resulting graph becomes visually useful in Obsidian without restructuring the vault.

**Files:**
- Modify local vault notes only
- Optional: `.obsidian/graph.json` in the local vault copy

**Step 1:** Preserve existing structure and colors.

**Step 2:** If needed, lightly tune `.obsidian/graph.json` so clusters by `me/`, `nexus/`, `knowledge/`, `workbench/` are easier to inspect.

**Step 3:** Do not create large numbers of weak canonical notes.

**Step 4:** Verify graph shape improves due to links, not due to taxonomy churn.

---

## Task 9: Weekly review and end-state verification

**Objective:** At the end of the week, prove the graph is materially more populated.

**Files:**
- Read only: progress notes, maintenance reports, maps, graph config, sample session notes

**Week-end success criteria:**
- local copy exists and is authoritative for nightly runs
- nightly job has run repeatedly without iCloud deadlock blocking the work
- wiki-progress score has trended upward across the week
- a substantial majority of readable session notes now have `## Curated links`
- canonical hubs are visibly linked into the session corpus
- `current-focus.md` and `banrawr-nexus-map.md` are genuinely useful entry points
- iCloud vault reflects the synced local improvements

**Verification commands:**
```bash
python -m pytest \
  tests/agent/test_vault_projection.py \
  tests/agent/test_vault_projection_local_sync.py \
  tests/agent/test_vault_projection_progress_metrics.py \
  tests/agent/test_vault_projection_curated_links.py \
  tests/run_agent/test_vault_projection_hooks.py \
  tests/tools/test_skill_manager_vault_projection.py \
  tests/cron/test_jobs_vault_projection.py \
  tests/scripts/test_nightly_brain_formation.py \
  tests/scripts/test_nightly_brain_formation_heartbeat.py -q
```

---

## Recommended implementation sequence for this week

### Day 1
- local copy bootstrap + safe sync helpers
- progress metrics skeleton

### Day 2
- curated-link pass for session notes
- first wiki-progress report

### Day 3
- nightly runner + heartbeat snapshots
- dry-run on local vault copy

### Day 4
- cron job activation
- first real nightly end-to-end run

### Day 5
- refine promotion rules and suppress noisy entities
- improve hub-note backlinks

### Day 6
- verify graph quality in Obsidian local copy
- sync polished changes back to iCloud

### Day 7
- weekly review report
- final score + before/after graph summary

---

## Implementation notes

- The local copy is not optional; it is the operational workaround for the iCloud deadlock issue.
- The progress bar should track **coverage**, not model confidence or vibe.
- Keep the weekly promotion target list intentionally small.
- The goal this week is a **populated knowledge graph within the existing structure**, not a perfect ontology.
- Use full-path wikilinks consistently.
- Prefer append/update over rewriting user-authored notes.
