# Lab notebook — KLend probe matrix + Wormhole governance forks

**Date:** 2026-06-13  
**SPEC:** v3.0.7  
**Continues:** v3.0.6 ordered path (deeper CPI + triage-scoped Wormhole)

## KLend probe account matrix

- `klend_probes.py`: `ProbeAccountSpec` per probe — oracle, KLend, KVault, SPL token, system program roles
- `klend_tx.py`: `build_signed_probe_transaction()` builds multi-account CPI invokes
- `klend_live_probes.py`: emits `PROBE_ACCOUNTS:` provenance line

**Live verify** (`NSS_KLEND_FIXTURE=0 KLEND_PROBE=oracle_staleness_borrow`):
- `PROBE_ACCOUNTS:oracle:HFn8GnPA,lending_market_program:KLend2g3,...`
- `PROBE_TX_CONFIRMED:1`, `PROBE_EXECUTED:1`, `MEASURED_DELTA_LAMPORTS:0` (fee-only → `live_deploy_verified`, not submittable)

## Wormhole triage governance depth

- New `foundry/test/WormholeTriage.t.sol`:
  - `testForkWormholeCoreGovernanceSurface` — guardian quorum, governance contract, malformed VM guard
  - `testForkWormholeBridgeGovernanceSurface` — transfer ledger, governance alignment with core
- `fork_targets.py`: live wormhole targets now use governance tests (getter tests retained in `ForkHistorical.t.sol`)

## Gates

- Still **0 submit_ready** — CPI lands with program accounts but no invariant break / no balance delta ≥ threshold

## Next

- KLend: clone mainnet reserve/oracle accounts for probe-specific CPI (needs account discovery)
- Wormhole: triage-scoped Foundry exploit skeleton on `BridgeGovernance.sol` pause/unpause auth paths