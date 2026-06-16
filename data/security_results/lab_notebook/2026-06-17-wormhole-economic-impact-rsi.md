# 2026-06-17 - Wormhole economic-impact RSI routing

## Context

The latest autonomous loop selected Wormhole via Solodit-backed untrusted proposals and refinement hints. Existing Wormhole Foundry harnesses verify governance/bridge/pauser surfaces, but they do not produce token/native deltas, bridge accounting violations, or bounded TVS-at-risk proof.

## Change

- Classified `triage_surface_requires_measured_delta`, `novel_fork_requires_balance_delta`, and Wormhole triage output with zero delta as `missing_economic_impact`.
- Routed that failure class to `generate_value_moving_poc`.
- Stamped Wormhole fork evidence with `economic_impact_verified` and set `failure_class=missing_economic_impact` when triage evidence lacks measured economic impact.
- Recorded a local Wormhole runtime trace for `TRIAGE_SURFACE_VERIFIED:1 balance_delta_wei=0` and regenerated `refinement_hints.json`. These runtime stores are ignored by git; the committed behavior is the classifier/fork-evidence code plus tests.

## Verification

```text
.venv/bin/python -m pytest tests/test_failure_trace_rsi.py tests/test_fork.py tests/test_wormhole_economic.py tests/test_task_verifier.py -q
28 passed

.venv/bin/python -m pytest tests/test_validation_layer.py tests/test_bounty_loop.py tests/test_failure_trace_rsi.py tests/test_fork.py tests/test_wormhole_economic.py tests/test_task_verifier.py -q
68 passed

.venv/bin/python -m pytest
404 passed, 5 skipped
```

## Result

No submit-ready bug. The next Wormhole lane should bind top semantic candidates to deployed core/token_bridge state and generate a candidate-specific value-moving assertion instead of repeating triage governance-surface replay.
