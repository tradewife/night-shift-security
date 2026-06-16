# Lab entry - KLend refresh prelude and stale oracle blocker

- date: 2026-06-16
- operator mode: autonomous orchestrator
- target: Kamino KLend
- lane: Solana validator-backed oracle borrow probe

## Observation

After borrower-side autosetup and Farms cloning, `borrow_obligation_liquidity_v2` still failed with `ReserveStale`. I added a source-derived refresh prelude and log capture to determine whether this was missing refresh wiring or price-status failure.

## System Change

- Added RPC-only KLend account refresh fallback because the Kamino metrics API returned `403`.
- Parsed Scope/Pyth/Switchboard oracle pubkeys from `Reserve.config.token_info`.
- Added Scope price account cloning for USDC/SOL reserves.
- Added `refresh_reserve(USDC)` and `refresh_obligation(new obligation)` before borrow.
- Warped current-state validator clones to the source RPC slot to avoid `LastUpdate::slots_elapsed()` underflow from local slot `0`.
- Captured transaction logs in `probe_results.jsonl`.
- Classified log-derived `PriceTooOld` paths as `oracle_price_too_old`.

## Verification

Focused tests:

```bash
.venv/bin/python -m pytest \
  tests/test_klend_account_discovery.py \
  tests/test_klend_tx.py \
  tests/test_klend_live_probes.py \
  tests/test_klend_harness.py \
  tests/test_validator_profiles.py -q
```

Result: `28 passed`.

Live command:

```bash
set -a && source .env && set +a
export NSS_KLEND_FIXTURE=0 NSS_HIPIF_BOUNTY_DEPTH=1 NSS_KLEND_AUTO_SETUP=1
export KLEND_PROBE=oracle_staleness_borrow
.venv/bin/python solana/run_klend_harness.py
```

Latest observed markers:

```text
SLOT_CURRENT:426855507
SLOT_WARP:426855507
PROBE_STATUS:on_chain_error:{"InstructionError": [2, {"Custom": 6009}]}
MEASURED_DELTA_LAMPORTS:0
PROTOCOL_DELTA_LAMPORTS:0
```

Latest JSONL:

```text
failure_class=oracle_price_too_old
tx_logs include "Price is too old age=11932 max_age=180"
tx_logs include "Price twap is too old token=[USDC]"
tx_logs include "price_status: 00110101"
```

Instruction index `2` confirms `refresh_reserve` and `refresh_obligation` completed before the borrow failed.

## Decision

This is still not submit-ready. The harness is now blocked on stale Scope oracle data in the cloned current-state account set, not account metas, missing executable programs, or stale validator slot. Next productive work is a fresh oracle-state strategy: find a live reserve/path with fresh price status, understand whether Scope is stale on mainnet for this market, or build a controlled local oracle-state experiment that remains clearly research-only.

