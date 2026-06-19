# Lab entry — coding-agent orchestrator (benchmark harness)

## Trigger
- manual — coding-agent outer loop session (not a Hermes cron job)
- commands: `hipif status`, `hipif gate`, `native status`, `pytest tests/test_benchmarks.py`

## State before
- native ready count: 7 (uniswap_v4, aave_v3, morpho_blue, kamino, jito, raydium, orca)
- Solana ready count: 4
- measured delta evidence: 7 `*_measured_delta.json` files under `data/security_results/impact/`
- candidate counts: ~2025 in `concrete_candidates.jsonl`
- latest submit_ready: false
- latest blocker: **B8_GATE_REJECTION_OK** — gates correct; no value-moving novel finding with measured impact + candidate PoC

## Change made
- files:
  - `benchmarks/expected/manifest.json` + EVM/Solana/meta fixtures
  - `src/night_shift_security/benchmarks/runner.py`
  - `tests/test_benchmarks.py`
  - `docs/agents/coding-agent-orchestrator-loop.md` — outer loop for Codex/Cursor (not Hermes runtime)
- rationale: Ship HTB-style benchmark harness; orchestration stays in coding-agent session, not a new Hermes cron.
- remediation (2026-06-19): removed accidental `nss-hermes-prime-bootstrap` cron recipe; moved prompt out of `hermes/prompts/`.

## Validation
- tests: `pytest tests/test_benchmarks.py tests/test_native_harness.py tests/test_bounty_loop.py tests/test_validation_layer.py` → 57 passed
- benchmark: 6/6 challenges pass (EVM vuln/patch, Solana vuln/patch, catalog not novel, Solodit untrusted)
- NSS/Hermes run: prior HIPIF complete (1540s, 13 folds, gate_ok, submit_ready=false)

## Same vs different
- what changed vs prior run: added benchmark regression suite (no gate edits); cron recipe removed after architecture correction
- what repeated: catalogue-only wormhole/kamino depth findings; refinement_hints wormhole top
- what failure fingerprint changed: none — still no submit_ready

## Gate result
- submit_ready: false
- gate_ok: true (13/13 folds)
- rejection reason: no finding with evidence grade ≥4, measured non-fee impact, candidate schema v4 + reproduction artifact

## Next action
- Hunt-to-submit on kamino with concrete_sequence + candidate-specific PoC generation (B5); run `pytest tests/test_benchmarks.py` before each substrate change.