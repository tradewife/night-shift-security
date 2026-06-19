# Lab entry — KLend refresh_reserve_live probe (kamino-native-001)

- date: 2026-06-19
- operator mode: autonomous orchestrator
- target: Kamino KLend / `kamino-native-001`
- lane: Solana validator-backed `refresh_reserve` binding

## Observation

`kamino-native-001` was routed to `oracle_staleness_borrow`, which prepended refresh prelude then failed at borrow with `oracle_price_too_old` (instruction index 2). The candidate binding is `refresh_reserve` only — borrow path is the wrong assay.

## System change

- Added `refresh_reserve_live` KLend probe (discriminator `0x02da8aeb4fc91966`, invariant `oracle_refresh_bound`).
- Routed `kamino-native-001` → `refresh_reserve_live` in `solana_validation._resolve_klend_probe_id`.
- Live probe reads reserve `last_update_slot` before/after; emits `RESERVE_LAST_UPDATE_SLOT_DELTA`.
- Harness promotes to `live_executed` when reserve slot delta > 0 (non-fee field measurement).
- Submission gates + PoC envelope accept `reserve_last_update_slot_delta` as measured impact.

## Verification

```bash
.venv/bin/python -m pytest tests/test_klend_harness.py tests/test_klend_probes.py \
  tests/test_klend_tx.py tests/test_klend_live_probes.py -q
```

Result: **28 passed**.

Live harness:

```bash
export NSS_KLEND_FIXTURE=0 KLEND_PROBE=refresh_reserve_live
.venv/bin/python solana/run_klend_harness.py
```

Markers:

```text
PROBE_STATUS:ok
PROBE_TX_CONFIRMED:1
PROBE:refresh_reserve_live
INVARIANT:oracle_refresh_bound
RESERVE_LAST_UPDATE_SLOT_DELTA:0
HARNESS_MODE:live_deploy_verified
```

Tx logs show `Instruction: RefreshReserve` success with stale Scope warnings; reserve slot unchanged on cloned state (already at warp slot). Mainnet cross-slot attestation (`kamino_measured_delta.json`) still provides `reserve_last_update_slot_delta=55`.

Kamino depth pass (`NSS_LOOP_DEPTH_SLUG=kamino`): **NSS-0010** (`kamino-native-001`) now carries `probe_id=refresh_reserve_live`, harness measured attestation, `impact_oracle.measured=true`, `reproduction_tier=solana_validator`. `solana_reproduced=false` (deploy-verified, not `live_executed`). `submit_ready` unchanged.

## Decision

Correct probe binding shipped. Validator replay executes `refresh_reserve` on-chain. Next bottleneck: raise evidence grade (≥4) and `submission_recommendation=submit_now` — requires `solana_reproduced` via live field delta or fresh Scope oracle strategy on clone.