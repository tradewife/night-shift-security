# Lab Notebook: Bounty Loop Fixes + KLend Live Probes

**Date:** 2026-06-19
**Session:** Morning (07:00-08:00 UTC)

## Summary

Fixed two critical bugs in bounty_loop.py and added three real KLend probes for deposit/redeem/flash-borrow instructions.

## Bug Fixes

### 1. bounty_loop.py env var leak
**Problem:** `os.environ["NSS_LOOP_DEPTH_SLUG"]` was set but never cleaned up, polluting test environment.
**Fix:** Wrapped in try/finally to restore original value. Extracted body to `_run_loop_iteration_body()`.
**Impact:** All 711 tests pass.

### 2. KLend probe account ordering
**Problem:** New probes had wrong account order, causing `AccountDiscriminatorMismatch` and `AccountOwnedByWrongProgram` errors.
**Fix:** Created `deposit_reserve_liquidity_probe_accounts()` and `redeem_reserve_collateral_probe_accounts()` per KLend IDL.
**Impact:** Probes now reach the correct instruction handler (though still failing on missing token accounts).

### 3. Collateral mint not cloned
**Problem:** `klend_clone_data_accounts()` didn't include collateral_mint, collateral_supply_vault, farm_collateral.
**Fix:** Added these to the default clone list.
**Impact:** Collateral mint accounts now cloned to local validator.

## New Probes Added

| Probe ID | Instruction | Discriminator | Status |
|----------|-------------|---------------|--------|
| deposit_reserve_liquidity_live | deposit_reserve_liquidity | 0xa9c91e7e06cd6644 | Executing but needs token account setup |
| redeem_reserve_collateral_live | redeem_reserve_collateral | 0xea75b57db98edc1d | Executing but needs token account setup |
| flash_borrow_reserve_liquidity_live | flash_borrow_reserve_liquidity | 0x87e734a70734d4c1 | Executing but needs token account setup |

## Current Evidence Grades

- **Total findings:** 62
- **Grade 0:** 0
- **Grade 1:** 62 (flash_loan_oracle: 12, concrete_sequence: 50)
- **Grade 3:** 0 (from previous run, now overwritten)

## Blockers

1. ~~**Token account setup:**~~ **DONE.** Added `_attempt_new_probe_setup()` in `klend_live_probes.py` that creates USDC + collateral ATAs via `spl-token create-account`. Wired into `_send_klend_invoke` for all 3 new probe IDs. Also fixed `deposit_reserve_liquidity_probe_accounts` (destination was USDC ATA, now collateral_mint ATA) and `redeem_reserve_collateral_probe_accounts` (source was USDC ATA, now collateral_mint ATA).
2. **CPCV bypass:** Concrete sequences have 0 catalog exploits, so CPCV is skipped. Need alternate Level-2 path for generic concrete sequences.
3. **Grade 1 stall:** Most findings stall at grade 1 because CPCV uses `flash_loan_oracle` catalog which flags all top candidates as DANGER.

## Next Steps

1. ~~Add token account setup for deposit/redeem probes~~ **DONE**
2. Test probes on validator to verify they execute (next session)
3. Run bounty loop with new probes to see if they produce grade 3+ findings
4. Focus on `treasury_drain` and `flash_loan_oracle` templates (0-1 catalog analogues)

## Commits

- `d2223d7` nss(v5): add live KLend probes, fix bounty_loop env leak, fix account ordering
- (uncommitted) fix: correct deposit/redeem collateral ATA derivation + add auto-setup for new KLend probes
