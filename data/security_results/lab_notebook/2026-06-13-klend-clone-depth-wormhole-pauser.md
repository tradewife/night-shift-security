# Lab notebook — KLend mainnet clone depth + Wormhole pause auth

**Date:** 2026-06-13  
**SPEC:** v3.0.8  
**Continues:** v3.0.7 probe matrix + governance forks

## KLend mainnet account cloning

- `sources/kamino/klend_accounts.json` — cached main market `7u3HeHxY...`, authority/global_config PDAs, USDC/SOL reserves + supply/fee vaults
- `solana/klend_account_discovery.py` — Kamino HTTP API refresh + optional RPC vault parse; `klend_clone_data_accounts()` for validator `--clone`
- `validator_profiles.py` — `clone_data_accounts` on `kamino-klend` (9 data accounts)
- `run_validator_replay.py` — `--clone` for data accounts alongside `--clone-upgradeable-program`
- `klend_probes.probe_account_specs()` — prepends market/reserve/vault metas before program accounts

**Live verify** (`NSS_KLEND_FIXTURE=0 KLEND_PROBE=oracle_staleness_borrow`):
- `CLONED_DATA_ACCOUNTS:7u3HeHxY...,D6q6wuQS...,Bgq7trRg...`
- `PROBE_ACCOUNTS:lending_market:7u3HeHxY,...,usdc_supply_vault:Bgq7trRg,...`
- `PROBE_TX_CONFIRMED:1`, `MEASURED_DELTA_LAMPORTS:0` → `live_deploy_verified` (fee-only, not submittable)

## Wormhole pause/unpause auth fork

- `testForkWormholeBridgePauserAuthSurface` in `WormholeTriage.t.sol`
- Reads pauser/unpauser from ERC-7201 namespace slot (live proxy lacks getter bubbling)
- Mainnet: both roles **unassigned** (`0x0`); unauthorized `pause()`/`unpause()` revert
- New fork target: `wormhole-token-bridge-pauser-ethereum` in `fork_targets.py` + `wormhole_triage.json`

## Gates

- Still **0 submit_ready** — deeper CPI account metas land txs but no invariant break / balance delta ≥ threshold

## Next

- KLend: wire real KLend instruction discriminators (replace `0xCAFE` prefixes) for reserve/oracle CPI paths
- Wormhole: governance-action skeleton on `SetPauserAddresses` (action 4) with signed VM fixture