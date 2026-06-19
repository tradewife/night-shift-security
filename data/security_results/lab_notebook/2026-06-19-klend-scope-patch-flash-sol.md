# Lab entry — KLend scope patch + flash SOL round-trip

- date: 2026-06-19
- operator mode: autonomous orchestrator (iteration continue)
- target: Kamino KLend / `kamino-klend`
- lane: validator clone depth — scope oracle unblock + flash atomicity

## Root cause (scope staleness on clone)

`solana-test-validator --warp-slot` starts with patched Scope `OraclePrices` timestamps aligned to warp `getBlockTime`, but **borrow setup txs advance the validator `Clock` unix_timestamp by ~54k seconds** before the main probe lands. KLend `refresh_reserve` then logs `Price is too old age=54099` and sets partial `price_status=00110101`, blocking borrow with `ReserveStale` (6009).

## System changes

- `solana/klend_scope_patch.py` — fetch/patch Scope `DatedPrice.unix_timestamp` for all populated entries; load via `--account` instead of `--clone` for `scope_prices`.
- `run_validator_replay.py` — `NSS_KLEND_PATCH_SCOPE=1` default; `SCOPE_PATCH` / `SCOPE_VERIFY` markers; depth-mode `meets_threshold` selection fix retained.
- Scope patch uses `scope_patch_unix_timestamp()` = warp block time + `NSS_KLEND_SCOPE_TS_BUFFER` (default 90000s) to survive post-setup clock drift.
- Flash probe: `NSS_KLEND_FLASH_RESERVE=SOL` default; wSOL prefund via `spl-token wrap` (no pre-create ATA); borrow+repay atomic tx succeeds.

## Verification

```bash
.venv/bin/python -m pytest tests/test_klend_scope_patch.py tests/test_klend_*.py tests/test_validation_layer.py -q
# 51 passed

export NSS_KLEND_FIXTURE=0 KLEND_PROBE=oracle_staleness_borrow
.venv/bin/python solana/run_klend_harness.py
# After scope buffer: ReserveStale cleared → ObligationDepositsEmpty (6020) — protocol-correct, no collateral

export NSS_KLEND_FIXTURE=0 KLEND_PROBE=flash_loan_collateral_loop NSS_KLEND_FLASH_RESERVE=SOL
.venv/bin/python solana/run_klend_harness.py
# PROBE_STATUS:ok — flash borrow+repay atomic, MEASURED_DELTA_LAMPORTS:0
```

## Decision

**continue** — no economic delta / non-fee exploit. Scope patch unblocks oracle-age path for deeper borrow/liquidation assays; next bottleneck is collateralized obligation setup + manipulation ix between flash borrow/repay. `submit_ready` unchanged.