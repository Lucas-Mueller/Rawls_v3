# Language Dynamics Audit

This document catalogs participant-facing strings in the experiment flow that bypass the translation system or rely on hard-coded English fallbacks. Each entry lists the location and a brief description of the non-dynamic language usage.

## Phase 1 Flow
- `core/phase1_manager.py:858` (also :872, :878, :892, :898, :912) – Counterfactual summaries insert the English token "Distribution" and dollar formatting directly into the output instead of delegating to the language manager for localized stage labels.

## Shared Utilities
- `core/distribution_generator.py:186` (also :197, :220, :231) – Principle explanations fall back to hard-coded English sentences when the language manager returns no value.
- `core/distribution_generator.py:486` – Average-row header defaults to the English word "Average" if translation lookup fails.
- `core/distribution_generator.py:514` – Constraint display appends the English fragment " of $..." rather than using a localized template.

## Phase 2 Services
- `core/services/discussion_service.py:182` – Group composition strings stitch names together with the English conjunction "and" instead of localization-aware list formatting.
- `core/services/discussion_service.py:267` (also :270, :275, :280) – Statement-validation fallbacks return English guidance/explanations/examples whenever translation keys are missing.
- `core/services/discussion_service.py:288` (also :293, :312) – Attempt-count and heading labels default to English phrases ("Attempt", "Statement Issue", "Your statement") for unknown languages.
- `core/services/counterfactuals_service.py:528` – Error fallback exposes the English sentence "Earnings display unavailable due to error..." to participants.
- `core/services/counterfactuals_service.py:569` (also :571) – Consensus fallback messages are hard-coded English sentences when localization fails.
- `core/services/counterfactuals_service.py:668` (also :685, :691, :708, :714, :731) – Counterfactual listings mirror the Phase 1 issue by embedding English "Distribution" labels and currency formatting inline.
- `core/services/counterfactuals_service.py:737` – Counterfactual failure fallback emits the English message "Counterfactual analysis unavailable.".

## Agent Surfaces
- `experiment_agents/participant_agent.py:232` – Default instruction string "You are a participant agent in the Frohlich Experiment. Respond concisely." bypasses localization when context is missing.
- `experiment_agents/utility_agent.py:829` (also :837, :869) – Parsing-feedback fallbacks rely on English explanations/samples whenever translation lookups fail or defaults are required.

## Observations
- Most primary prompts already route through translation files, but fallback branches and stitched helper strings remain English-only.
- Replacing these strings with language-manager lookups (and adding the missing keys to translation files) would close the remaining localization gaps.
