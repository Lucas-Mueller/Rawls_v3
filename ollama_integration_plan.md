# Ollama Chat Completions Integration Plan

## Context & Current State
- Model routing today is centralized in `utils/model_provider.py`. It normalizes the configured model string, chooses between the `openai`, `gemini`, and `openrouter` families, and returns either a plain model name (OpenAI) or an `OpenAIChatCompletionsModel` that wraps an `AsyncOpenAI` client.
- `create_model_config*` helpers feed directly into participant agent construction (`experiment_agents/participant_agent.py`) and the dynamic temperature detection helpers in `utils/dynamic_model_capabilities.py`.
- Provider-specific clients live in dedicated helpers (`utils/openrouter_client.py`, `utils/gemini_client.py`) that memoize an `AsyncOpenAI` instance with provider-specific `base_url` and credentials.
- Unit tests in `tests/unit/test_model_provider.py` and `tests/unit/test_model_provider_info.py` codify the current detection logic, nitro suffix handling, and environment messaging. Integration smoke tests live in `test_gemini_integration.py`.
- Any model name containing `/` is currently treated as OpenRouter, so adding a new prefixed provider will require restructuring that guard.

## Goals
1. Allow experiments to target local Ollama models surfaced through the experimental OpenAI-compatible API (`http://localhost:11434/v1`).
2. Keep configuration ergonomics consistent with existing providers (per-agent `model` string, optional temperature) while making the provider intent explicit.
3. Reuse the existing `OpenAIChatCompletionsModel` pathway so streaming, structured outputs, and tracing continue to function unchanged.
4. Maintain clear validation and error messaging when prerequisites (running Ollama daemon, pulled model) are missing.
5. Extend the automated test matrix to cover Ollama detection and configuration without requiring the runtime to actually contact a local daemon.

## Implementation Steps
1. **Introduce Ollama client helper**
   - Add `utils/ollama_client.py` modeled after the existing client helpers.
   - Default `base_url` to `http://localhost:11434/v1` and accept overrides via `OLLAMA_BASE_URL`.
   - Default `api_key` to the sentinel value `ollama`, but allow `OLLAMA_API_KEY` for completeness. Memoize the resulting `AsyncOpenAI` client (`lru_cache`).
   - Log a single-line info message confirming initialization for troubleshooting.

2. **Extend provider detection**
   - Update `detect_model_provider` to recognize an `ollama/` prefix (before the generic `/` → OpenRouter rule) and map it to the new provider.
   - Decide on handling bare model names (e.g., `llama3.2`). Options:
     1. Require the explicit `ollama/` prefix to avoid collisions with unknown providers (keeps current failure behavior but with a clearer error about adding the prefix), or
     2. Allow a configurable fallback (e.g., if `OLLAMA_DEFAULT_PROVIDER=true`). Document whichever path we pick.
   - Ensure returned tuple contains the normalized model name (`llama3.2` or whatever follows the prefix) and the provider string `"ollama"`.
   - Update error messages to include Ollama guidance (e.g., “Use `ollama/<model>` or pull the model locally”).

3. **Refresh legacy adapter & downstream checks**
   - Teach `detect_model_provider_legacy` to translate the new provider into the legacy boolean (likely treating Ollama as `False`, similar to OpenAI, since Nitro suffix logic should not apply).
   - Audit any remaining code paths that assume only two providers; adjust descriptive comments and conditions so they gracefully handle `provider == "ollama"`.

4. **Wire `create_model_config` family**
   - Add an Ollama branch in `create_model_config` that builds an `OpenAIChatCompletionsModel` with the cached client and the raw model string (no suffixing).
   - Mirror the same branch in `_create_conservative_model_config` and `create_model_config_with_temperature_detection` so temperature probing passes the correct object downstream.
   - Update logging statements to include the new provider for easier debugging.

5. **Temperature detection adjustments**
   - Review `utils/dynamic_model_capabilities.py` usage. Anywhere the code inspects `is_openrouter` should consider Ollama explicitly (e.g., skip Nitro suffix, decide on conservative assumptions about temperature support—probably optimistic since Ollama exposes temperature).
   - If necessary, refactor helper signatures to pass the provider string instead of the Boolean to avoid future condition creep, while maintaining backwards compatibility for existing callers.

6. **Configuration & documentation updates**
   - Document new environment variables (`OLLAMA_BASE_URL`, optional `OLLAMA_API_KEY`) and usage in `README.md` and relevant docs under `docs/` (installation/getting-started sections).
   - Provide a sample agent snippet in `config/default_config.yaml` comments or a dedicated example config showing `model: "ollama/llama3.2"`.
   - Mention prerequisite steps (`ollama serve`, `ollama pull <model>`) and call out that OpenAI compatibility is experimental.

7. **Testing strategy**
   - Expand `tests/unit/test_model_provider.py` to cover detection, model config creation, and Nitro suffix avoidance for Ollama (mocking the client and `OpenAIChatCompletionsModel`).
   - Add assertions to `tests/unit/test_model_provider_info.py` for the new provider metadata.
   - Update `test_gemini_integration.py` (or create a sibling script) with optional smoke output that only runs when `OLLAMA_BASE_URL` is reachable, while ensuring CI environments skip gracefully.
   - Consider adding a lightweight integration test guarded by an environment flag that exercises the chat completions path end-to-end when a local daemon is available.

8. **Operational validation**
   - After implementation, run targeted experiments using an Ollama-backed agent to verify:
     - Non-streaming and streaming replies.
     - Temperature variations if supported.
     - Structured output parsing (where applicable).
   - Monitor logs for tracing metadata to ensure spans capture the custom base URL without leaking credentials.

## Risks & Open Questions
- **Naming collisions**: Without explicit prefixing, arbitrary model strings could be misrouted. Requiring `ollama/` keeps behavior deterministic but adds a mild config burden.
- **Feature parity**: Ollama’s OpenAI compatibility may not support every Agents SDK capability (tools, JSON schema). Need to document any gaps discovered during validation.
- **Local daemon availability**: Experiments will hang if the Ollama server is down. Consider adding a startup health check or clearer error surfacing during client initialization.
- **Temperature semantics**: If Ollama ignores temperature, dynamic detection may flag it as unsupported. Be prepared to adjust conservative defaults based on empirical results.

## Deliverables
- Code updates across `utils/model_provider.py`, new `utils/ollama_client.py`, temperature helper adjustments, and updated tests/docs.
- Verified Markdown documentation describing configuration and operational guidance.
- (Optional) Example configuration file highlighting an Ollama-backed experiment setup.
