# Night Shift Security — Technical Specification

**Version:** 1.6  
**Date:** 2026-06-08  
**Author:** Grok (for Kate / tradewife)  
**Purpose:** Define the Hypothesis Generation Layer and its evolution.

---

## Current State (as of 2026-06-08)

**v1.5 merged into main** — Real LLM Provider Integration:
- Swappable `llm_provider.py` abstraction (`LLMProvider`, `LiteLLMProvider`, `MockLLMProvider`).
- `LLMExpansionOrchestrator` calls a real provider when `llm_expansion.enabled: true`.
- Parametric fallback preserved when LLM is disabled, misconfigured, fails, or returns invalid output.
- Every LLM proposal passes `validate_hypothesis()` before pipeline handoff.
- Basic observability via `logging` (call success/failure, token counts, rough cost estimates).
- Config extended with `provider`, `model`, `api_key_env`, `temperature`, `max_tokens`, `timeout_seconds`.
- Optional dependency: `pip install -e ".[llm]"` installs LiteLLM for production calls.
- 120+ tests passing (mocked LLM path in CI).

**v1.4** (prior): Full Hypothesis Generation Layer for all 7 templates, versioned mapping, lineage provenance, pipeline integration.

---

## Enabling LLM Expansion

1. Install optional LLM dependency:
   ```bash
   pip install -e ".[llm]"
   ```
2. Set API key (example for OpenAI via LiteLLM):
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
3. Enable in config (`config/default.json` or override):
   ```json
   {
     "llm_expansion": {
       "enabled": true,
       "provider": "litellm",
       "model": "gpt-4o-mini",
       "api_key_env": "OPENAI_API_KEY",
       "fallback": "parametric",
       "variants_per_seed": 2,
       "max_seeds": 5
     }
   }
   ```

**Provider notes**:
- `provider: "litellm"` — uses LiteLLM; supports OpenAI, Anthropic, Grok (`xai/grok-*`), and other LiteLLM backends via `model` string.
- `api_key_env` — environment variable name for the API key (default `OPENAI_API_KEY`).
- `api_base` — optional override for custom endpoints.
- LLM output is **untrusted**; `metadata.trusted = false` on all proposals.

---

## LLM Integration Architecture

```
llm_expansion.enabled=true
        │
        ▼
create_llm_provider(config)  ──► LiteLLMProvider (or inject MockLLMProvider in tests)
        │
        ▼
LLMExpansionOrchestrator.propose_variants(seed)
        │
        ├─► LLM JSON proposals ──► validate_hypothesis() ──► accepted
        │
        └─► on failure / invalid ──► parametric mutate() fallback ──► validate_hypothesis()
```

**Safety invariants** (unchanged):
- LLM never participates in validation, scoring, or gate decisions.
- Stages 4–6 and reproduction harnesses unchanged.
- Failed LLM calls never crash the pipeline.

---

## Previous Versions (for reference)

**v1.5**: Real LLM provider integration behind `llm_expansion` hook.  
**v1.4**: Full Hypothesis Generation Layer + versioned mapping + lineage tracking.  
**v1.3 / v1.2**: Initial `attack_hypotheses/` package and pipeline wiring.

---

*End of v1.6 update. Next focus: lineage survival analytics, early structural filters.*