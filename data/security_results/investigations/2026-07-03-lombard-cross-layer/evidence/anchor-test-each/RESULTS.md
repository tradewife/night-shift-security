# Anchor Test (Per-File) Results — v6.51 Lombard Pass 2

**Date**: 2026-07-04
**Run**: `bash scripts/anchor-test-each.sh` with `ANCHOR_TEST_EACH_SLEEP_SECONDS=15`
**Outcome**: **all files passed** when each gets a fresh ledger (isolated `solana-test-validator` per file).

## Per-file results

| File | Passing | Time |
|------|---------|------|
| `tests/asset_router.ts` | 85 | 1m |
| `tests/bascule.bankrun.test.ts` | 12 | 2s |
| `tests/bascule.ts` | 1 | 10s |
| `tests/bascule_gmp.ts` | 21 | 9s |
| `tests/bridge.ts` | 71 | 2m |
| `tests/ccip.ts` | 7 | 31s |
| `tests/consortium.ts` | 17 | 8s |
| `tests/consortium_utilities.spec.ts` | 23 | 9s |
| `tests/mailbox.ts` | 54 | 37s |
| `tests/ratio_oracle.ts` | 18 | 7s |
| `tests/registry.ts` | 1 | 711ms |

**Total passing (per-file run): 310 tests across 11 TS suites**.
(Skipped `tests/lbtc.ts` per the script; runs in `anchor test` aggregate.)

## Implication

The 16 failures observed in the *aggregate* `anchor test` run (149/165) are pure devnet/validator **shared-state cross-pollution** between test files run in one validator session — **NOT protocol bugs**. PDAs that are globally reused (e.g., consortium program owner at `12y3Uh6srjcnfjr7iFTn8vEVhrqf3vs7aAGiBfR61SUU`, and bridge mailbox/pool accounts at `8SFqwq…`, `BqScmy…`) collide when subsequent `before all` hooks attempt to allocate them, while successful prior files in the same ledger have already left them occupied.

Per-file or per-program isolation restores the green signal. Lombard protocol behavior is correct under fresh-ledger, fresh-validator conditions. The protocol's replay/init dedupe is delegated to PDA `init`, which gives correct semantics only when each test owns a clean ledger.

## Adjudication

- **Previous v6.49/24 honest-zero** for cross-layer replay is upheld (no findings).
- **Honest-zero for v6.51 (lombard_token_pool)** confirmed under all 310 isolated tests.
- Move v6.51 strategy execution forward (Crucible stateful sequences + EVM divergence probes); no false alarms.
