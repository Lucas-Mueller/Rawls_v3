# Contract Test Playbook

Contract tests live under `tests/contracts/` and assert on golden artefacts
produced by live experiment runs. They intentionally keep assertions stable, so
updates must be deliberate.

## When to Run
- Local sanity check: `pytest tests/contracts`
- Mode preset: `pytest --mode=full -m contracts`
- CI: included in nightly/full matrix jobs when credentials are available

## Updating Golden Artefacts
1. Make the code change that legitimately alters a contract output.
2. Run the affected contract test(s) with `pytest -k <test_name> tests/contracts`.
3. Inspect the generated diff (usually under `tests/contracts/fixtures` or
   similar) and confirm the change is intentional.
4. Update the golden file(s) in-place, commit alongside the code change, and
   mention the contract refresh in your PR notes.

## Credentials & Skips
Contract tests do not require live LLM access. If a future contract depends on
API output, mark it with `@pytest.mark.live` and document any required keys.

## Review Checklist
- [ ] Contract change explained in PR description
- [ ] Golden diff reviewed for accidental redactions or secrets
- [ ] Tests pass locally (`pytest tests/contracts`)
- [ ] Follow-up component/integration tests adjusted if behaviour changed

Keeping contracts small and purpose-built ensures reviewers can reason about
changes quickly while maintaining high confidence in public artefacts.
