# 2026-07-04 (addendum) — Lombard cross-layer v6.51 round 2: Crucible unblocked, per-file tests green, EVM vs Solana divergence mapped

## What changed since the v6.51 baseline

### Crucible scaffold recovered

The earlier blocker (`LiteSVM/InvalidAccountData` loading `target/deploy/lombard_token_pool.so`) was caused by the scaffold pulling the SBF release binary while the workspace had built the mainnet-feature .so. Resolution was direct: copy the mainnet-feature `.so` from `target/deploy/` (686 512 B; ELF 64-bit arch 0x107) into the Crucible scaffold's `target/deploy/`, then re-run `crucible run lombard_token_pool invariant_test --dry-run`.

Final dry-run reports: **"DRY-RUN Harness Validation passed! - 1 tracked accounts - 1 programs loaded - Single iteration completed successfully"**. Captured to `data/security_results/investigations/2026-07-03-lombard-cross-layer/evidence/crucible-lombard-token-pool-dry-run.log` and `…/crucible-lombard-token-pool-dry-run-2.log`.

Signal `BLOCKER-CRUCIBLE-001` is now `RESOLVED`.

### Anchor TS aggregate vs per-file adjudication

Aggregate `anchor test --skip-build -- --features localnet --no-default-features` run over the full Lombard repo: **149 / 165 passing, 16 failing**, all in `before all` hooks sharing globally-derived PDAs (consortium owner at `12y3Uh6srjcnfjr7iFTn8vEVhrqf3vs7aAGiBfR61SUU`, mailbox deploy keys at `8SFqwqnq4whPhs8icwHA2hQg3hUoN1qrCLK1SBx3WKwe`, rate-limit PDAs at `BqScmyjmK7f3sxvPk4f4ikUHAKT4AYUKMjp8edSQURZb`). When subsequent suites try to allocate these in the same validator session, they hit `Allocate/Create Account ... already in use`.

Per-file isolated ledger via `scripts/anchor-test-each.sh` with `ANCHOR_TEST_EACH_SLEEP_SECONDS=15`:

| File | Passing | Time |
|------|---------|------|
| `asset_router.ts` | 85 | 1m |
| `bascule.bankrun.test.ts` | 12 | 2s |
| `bascule.ts` | 1 | 10s |
| `bascule_gmp.ts` | 21 | 9s |
| `bridge.ts` | 71 | 2m |
| `ccip.ts` | 7 | 31s |
| `consortium.ts` | 17 | 8s |
| `consortium_utilities.spec.ts` | 23 | 9s |
| `mailbox.ts` | 54 | 37s |
| `ratio_oracle.ts` | 18 | 7s |
| `registry.ts` | 1 | 711ms |

**Per-file: ALL GREEN. 310 passing across 11 TS suites.**

This adjudicates the aggregate's 16 failures as validator shared-state cross-pollution, **not protocol bugs**. Signal `BLOCKER-VALIDATOR-001` is now `RESOLVED`. Saved to `data/security_results/investigations/2026-07-03-lombard-cross-layer/evidence/anchor-test-each/RESULTS.md` and `…/summary.log`.

### Cross-layer EVM vs Solana divergence (round-2 insight) — SIG-XR-003-EVM-DIVERGENCE

`scenarios.lombard.Mailbox._deliverAndHandle` and `programs/mailbox/src/instructions/handle_message.rs` diverge on what happens when the handler program reverts:

- **EVM (Mailbox.sol):** wraps `try IHandler(payload.msgRecipient).handlePayload(payload)` inside `try/catch`. Failure populates a `handledPayload[payload.hash] = false` slot and **never bubbles the revert**. Failed mail remains `Delivered` forever and a fresh `deliverAndHandle` tx can re-attempt with the same `payload.id` (still gated by `payloadSpent` → `false`).
- **Solana (mailbox.handle_message.rs):** writes `message_info.status = Handled` **before** `invoke_signed(instruction: bridge.gmp_receive, signer_seeds: [MESSAGE_SEED, payload_hash, bump])`. If the recipient CPI reverts, Anchor transaction atomicity rewinds the `Handled` write so the message returns to `Delivered`. A fresh tx is required to re-attempt with the same payload hash.

In both chains, [MESSAGE_SEED, payload_hash] PDA `init` is the dedupe guard, so a literal replay cannot pass init. The distinguishing behaviour is the **retry semantics**:

- Solana: one gmp_receive failure atomically unwinds the entire CPI flow including mailbox, rate-limit, token mint, and balance change.
- EVM: handler revert stays local to the call; the bridge's surrounding `_withdraw` (and Bascule `validateMint`) will not have run yet (they live inside the catch'd handlePayload). Subsequent `deliverAndHandle` retries the same payload, with the rate-limit and Bascule checks still authoritative.

**Adjudication**: This is a documented cross-layer design divergence, not a Lombard bug. Both code paths retain their Bascule and rate-limit gates — the only difference is whether a single try/catch bubbles or rolls back. Hardhat probe adding value: `Mailbox._deliverAndHandle` with a revert-throwing handler must leave `handledPayload[payload.hash] == false` AND `payloadSpent[payload.id] == false`, allowing the same payload to be retried.

### Adjudication on `release_or_mint_tokens` rollback

Because per-file tests green-light all 54 `mailbox.ts` cases including `gmpReceive rejects when invalid recipient account`, the protocol-side `destination_caller` boundary is well-defended through unit-level evidence. The remaining verdict is reserved for an end-to-end cross-program fixture described in `next_steps`.

## Next actions (carry-forward)

1. Single-file Anchor TS integration in `tests/lombard_cross_layer_v651.ts`:
   - `release_or_mint_tokens` with `destination_caller == state PDA` → success.
   - `release_or_mint_tokens` with `destination_caller == pool_signer` → revert `InvalidDestinationCaller`.
   - `release_or_mint_tokens` with downstream `bridge.gmp_receive` failing (forced via absent `message_handled` PDA) → mailbox status returns to `Delivered` and recipient balance unchanged.
   - Decimal mismatch `release_or_mint_tokens` → full rollback, rate-limit not consumed.
2. Crucible stateful sequence action set:
   - `init_global_config`, `initialize_token_pool`, `init_chain_remote_config`, `set_remote_chain_rate_limit`,
     `deliver_message_mock`, `release_or_mint_succeed`, `release_or_mint_revert_due_to_amount_mismatch`,
     `release_or_mint_revert_due_to_destination_caller_mismatch`.
3. Hardhat EVM probes:
   - `Mailbox._deliverAndHandle` with revert-throwing handler — confirm re-attempt capability.
   - `AssetRouter._changeBascule(address(0))` admin disable-mint path.
4. Deepen `STRAT-S1` (`gmp-cross-layer-replay`) with the EVM-vs-Solana divergence mapping.

## Gate

Still no Lombard cross-layer issue is submission-ready. `submit_ready` remains 1 from OnRe H1 v6.13.
