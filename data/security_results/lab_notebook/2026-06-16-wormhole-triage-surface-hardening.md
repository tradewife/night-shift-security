# Lab entry — Wormhole triage-surface hardening

- date: 2026-06-16
- operator mode: autonomous orchestrator
- target: Wormhole
- proposal source: `data/security_results/hermes_proposals/latest.json`

## Observation

Ran a focused Wormhole proposal pass with `.env` loaded:

```bash
set -a && source .env && set +a
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/wormhole_triage.json \
  --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --target wormhole --iterations 1 --trials 4
```

Initial output showed stable fork-surface signal:

- `proposal_target_match=true`
- `fork_reproduced=48`
- evidence grade 4
- recommendation: `polish_validator`
- no `qualifies=true`

Inspection of `NSS-0003` showed this was not a value-moving repro:

- `fork_evidence.balance_delta_wei=0`
- `fork_evidence.verifier_method=catalog_exempt`
- `fork_evidence.triage_surface_verified=true`
- no v4 candidate payload
- generated reproduction script was a stub
- shoestring pack declared `export_track=research_surface`

## System Change

Hardened `apply_verifier_to_fork_entry()` so triage-surface EVM fork checks with no measured delta cannot remain `fork_reproduced`.

This preserves the surface-confirmation artifact for research but prevents it from receiving reproduction credit or inflating bounty exports.

## Verification

Focused tests:

```bash
.venv/bin/python -m pytest \
  tests/test_task_verifier.py \
  tests/test_fork.py \
  tests/test_wormhole_economic.py \
  tests/test_harness_gate.py \
  tests/test_bounty_loop.py -q
```

Result: `55 passed`.

Reran a focused Wormhole proposal pass with RPC loaded:

- `fork_confirmed=42/42`
- `fork_reproduced=0`
- Immunefi packs: 0
- best recommendation: `hold`
- submit candidates: 0

## Decision

Treat the previous Wormhole access-control cluster as a false-positive triage surface, not a bug candidate.

Next productive direction is candidate-specific measured-delta work:

- Wormhole: bind v4 concrete candidates to real message/accounting deltas, not governance getter surfaces.
- KLend/Kamino: continue live validator/value-delta path because it already produces real Solana execution evidence.
