# Lab notebook — KLend CPI, Wormhole getters, loop hardening

**Date:** 2026-06-13  
**SPEC:** v3.0.6  
**Session:** Day Shift continuation — ordered path (1) KLend CPI → (2) Wormhole depth → (3) cron/loop hardening

## What changed

### 1. Live KLend CPI (measured deltas only)

- `solana/klend_tx.py`: `solders`-backed signed invoke builder (`build_signed_invoke_transaction`)
- `solana/klend_live_probes.py`: CPI send inside validator lifecycle; `failed_on_chain` counts as executed
- `solana/run_validator_replay.py`: runs probe before validator shutdown when `KLEND_HARNESS=1` + `KLEND_PROBE`
- `solana/run_klend_harness.py`: parses probe markers; `PROBE_EXECUTED:1` on deploy path when tx lands (fee delta below threshold stays `live_deploy_verified`)
- `pyproject.toml`: optional `solana` extra (`pynacl`, `solders`)
- `tests/test_klend_tx.py`: tx builder unit tests

**Live run:** `NSS_KLEND_FIXTURE=0 KLEND_PROBE=oracle_staleness_borrow` → `PROBE_TX_CONFIRMED:1`, tx sig on local validator, `MEASURED_DELTA_LAMPORTS:0` (fee-only; no `live_executed` — correct for submit gate).

### 2. Wormhole program-specific fork depth

- `foundry/test/ForkHistorical.t.sol`: `testForkWormholeCoreLiveGetters`, `testForkWormholeTokenBridgeLiveGetters` (chainId, guardian set, wormhole() wiring)
- `fork_targets.py`: live targets point at getter tests (not bytecode-only)
- Forge verified on mainnet fork with `ETHEREUM_RPC_URL`

### 3. Bounty loop / cron hardening

- `bounty_loop.py`: Wormhole override → `wormhole_triage.json`; Kamino loop sets `klend_require_live`; triage config enables live fork targets
- `hermes/skills/bounty-loop/SKILL.md`: documents credible KLend + Wormhole triage gates
- Tests: `test_build_loop_config_*`, `test_fixture_klend_finding_not_submit_candidate`, `test_wormhole_live_fork_targets_use_getter_probes`

## Gates (unchanged intent)

- **0 submit_ready** for fixture/synthetic KLend or deploy-only evidence
- `live_executed` requires measured delta ≥ `OPERATOR_LAMPORT_THRESHOLD`

## Next

- KLend probe matrix: wire probe-specific account metas for deeper CPI (still non-submittable until real invariant break)
- Wormhole: triage-scoped Foundry PoC beyond getter smoke on `ethereum/contracts/Wormhole.sol`