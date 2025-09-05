# Structured Mode Regression Analysis and Restoration Plan

## Executive Summary
- Structured memory mode (organized, bullet-style prompts) regressed in at least one Phase 2 path.
- The primary regression is that `TwoStageVotingManager` derives `memory_guidance_style` from `Phase2Settings` (which has no such field) and falls back to `"narrative"`, bypassing experiment config and `MemoryService`.
- Additional inconsistency: `MemoryService`’s default was changed to `"structured"` when no config is provided, contradicting unit tests and creating divergent defaults.
- Configuration defaults in `ExperimentConfiguration` remain `"narrative"`, but `config/default_config.yaml` sets `"structured"`. If YAML is used (default run path), structured mode should be active—except where code incorrectly sources the style from settings.

## What “Structured Mode” Means Here
- Controlled by `memory_guidance_style` = `"structured" | "narrative"`.
- Implemented in `utils/memory_manager.py::_create_memory_update_prompt` via template selection:
  - `structured` → `prompts.memory_memory_update_prompt` (and `_no_recent_activity` variant)
  - `narrative` → `prompts.memory_narrative_update_prompt` (and `_no_recent_activity` variant)
- Translation keys exist for both base and `_no_recent_activity` variants in `translations/*_prompts.json`.

## Symptoms Observed
- Memory updates after two‑stage voting were produced with narrative-style prompts despite config requesting `structured`.
- Structured prompts still used in other paths that route memory updates through `MemoryService`.

## Systematic Findings (search-driven)
- Config values
  - `config/default_config.yaml`: `memory_guidance_style: "structured"` (intended default for runs).
  - `config/models.py (ExperimentConfiguration)`: default is `"narrative"` (sane default for programmatic construction; YAML overrides it at runtime).
- Memory service and managers
  - `core/services/memory_service.py`:
    - Constructor sets `self.memory_guidance_style = ... 'structured' if config else 'structured'` → default becomes `structured` when no config is passed. Unit test expects `narrative` as default.
    - All complex updates flow through `SelectiveMemoryManager` with `memory_guidance_style` explicitly forwarded from `MemoryService`.
  - `utils/selective_memory_manager.py`:
    - For complex events, it extracts style from `config.memory_guidance_style` when provided; otherwise defaults to `"narrative"`.
  - `utils/memory_manager.py`:
    - Implements prompt key switching for `structured` vs `narrative`.
- Phase orchestration
  - `core/phase2_manager.py`:
    - Correctly constructs `MemoryService(config=experiment_config)` so style should reflect YAML.
  - `core/two_stage_voting_manager.py`:
    - BUG: At lines ~1125–1127, it updates memory via `MemoryManager.prompt_agent_for_memory_update(...)` with:
      - `memory_guidance_style = getattr(self.settings, 'memory_guidance_style', 'narrative')`.
      - `Phase2Settings` does not define `memory_guidance_style`, so this always resolves to `"narrative"`, ignoring experiment config and `MemoryService`.
    - Other places in this module correctly use `self.memory_service.update_*` helpers, which honor the experiment config.
- Phase 1
  - `core/phase1_manager.py`: uses `config.memory_guidance_style` (correct source of truth).

## Root Causes
1) Incorrect source of truth in `TwoStageVotingManager` for memory style
- Uses `self.settings` (Phase2Settings) instead of experiment config or `MemoryService`, so it silently defaults to `narrative`.

2) Divergent default in `MemoryService`
- Defaulting to `"structured"` when `config=None` contradicts unit tests (`tests/unit/test_memory_service.py`) that expect `"narrative"` default.

3) Split configuration semantics
- `ExperimentConfiguration` (source of truth) vs `Phase2Settings` (operational knobs) caused accidental style lookups from the wrong config namespace.

## Impacted Paths
- Post–two-stage voting “complete delta” memory update in `TwoStageVotingManager` (lines ~1125–1127).
- Potential unit-test failures for `MemoryService` due to the changed default.

## What To Change (precise)
- TwoStageVotingManager
  - Replace the direct call to `MemoryManager.prompt_agent_for_memory_update(...)` with a call through `MemoryService` (preferred) or, minimally, fetch the style from `self.memory_service.memory_guidance_style` (or the experiment config) instead of `self.settings`.
  - Option A (preferred): add a small helper in `MemoryService` for “append complete voting delta” and use it here; or call `update_memory_selective` with an appropriate event type (e.g., `PHASE_TRANSITION` or `SIMPLE_STATUS_UPDATE`) and the assembled content.
  - Option B (minimal):
    - `memory_guidance_style = getattr(self.memory_service, 'memory_guidance_style', 'narrative')`
    - Keep the existing `MemoryManager` call but with the correct style.

- MemoryService default
  - Set `self.memory_guidance_style` to `"narrative"` when `config=None` to match tests and the broader default philosophy (YAML upgrades to structured).

- Guardrail test (optional but recommended)
  - Add a small unit/integration test ensuring `ExperimentConfiguration(memory_guidance_style="structured")` produces structured prompts through two‑stage voting path (mock MemoryManager to capture `memory_guidance_style`).

## Step‑by‑Step Plan To Reinstate Structured Mode
1) Fix `TwoStageVotingManager` style source
- Change the style lookup to use `self.memory_service.memory_guidance_style` (or route through `MemoryService.update_memory_selective`).
- Rationale: Centralize style policy in one place (MemoryService / ExperimentConfiguration).

2) Align `MemoryService` default
- Update constructor to default to `"narrative"` when `config=None` (keeps tests green, avoids silent behavior changes in programmatic contexts).

3) Optional centralization (future hardening)
- Add a single helper (e.g., `utils/config_helpers.get_memory_style(config, memory_service=None)`) or just treat `MemoryService` as the source of truth and prohibit direct `MemoryManager` calls in services.

4) Validation
- Run `python run_tests.py unit` and confirm `tests/unit/test_memory_service.py` default‑style assertions.
- Run targeted integration tests touching voting and memory: `tests/integration/test_phase2_memory_write_paths.py` and `tests/integration/test_phase2_voting_integration.py`.

## Risks and Mitigations
- Risk: Changing the memory path in `TwoStageVotingManager` could slightly alter memory content formatting due to different event typing.
  - Mitigation: Use minimal change (Option B) first to preserve content; then refactor to `MemoryService` later.
- Risk: Default shift in `MemoryService` could affect ad‑hoc usage without config.
  - Mitigation: This matches unit tests; structured remains available via YAML or explicit config.

## Concrete Diff Guidance
- File: `core/two_stage_voting_manager.py`
  - Replace:
    - `memory_guidance_style = getattr(self.settings, 'memory_guidance_style', 'narrative')`
    - with `memory_guidance_style = getattr(self.memory_service, 'memory_guidance_style', 'narrative')`
  - Or, better: `context.memory = await self.memory_service.update_memory_selective(..., event_type=MemoryEventType.SIMPLE_STATUS_UPDATE, content=memory_content)`

- File: `core/services/memory_service.py`
  - In `__init__`, change default when `config is None` from `'structured'` to `'narrative'`:
    - From: `self.memory_guidance_style = getattr(config, 'memory_guidance_style', 'structured') if config else 'structured'`
    - To:   `self.memory_guidance_style = getattr(config, 'memory_guidance_style', 'narrative') if config else 'narrative'`

## Quick Verification Checklist
- With `config/default_config.yaml` → structured prompts observed in discussion and voting memory updates (including the post‑voting delta).
- With ad‑hoc code‑constructed config and no style set → narrative by default (tests pass).
- `SelectiveMemoryManager` continues to honor config style for complex events; simple appends remain format‑agnostic.

## Appendix: Key References
- Style sources
  - `config/default_config.yaml`: `memory_guidance_style: "structured"`
  - `config/models.py (ExperimentConfiguration)`: default `"narrative"`, validator enforces {narrative, structured}
- Memory routing
  - `core/services/memory_service.py` → central entry → `SelectiveMemoryManager`
  - `utils/selective_memory_manager.py` → complex events → `utils/memory_manager.py`
- Regression point
  - `core/two_stage_voting_manager.py` lines ~1125–1127 → style from `self.settings` → always `"narrative"`
- Defaults mismatch
  - `tests/unit/test_memory_service.py` expects `MemoryService(...).memory_guidance_style == 'narrative'` by default.

---

If you’d like, I can implement the minimal fix in `TwoStageVotingManager` and align the `MemoryService` default now, then run unit tests to validate.

