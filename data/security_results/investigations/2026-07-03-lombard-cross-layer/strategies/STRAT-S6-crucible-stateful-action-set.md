# STRAT-S6 — Crucible stateful action set on `lombard_token_pool` (v6.51)

## Status: SCAFFOLD LIVE, EXPANSION DEFERRED

This is the carry-forward strategy from the v6.51 scaffolding step. The scaffold
is the only Crucible artifact that has been revived (the prior attempt had a
`InvalidAccountData` blocker on LiteSVM loading the mainnet `.so`). The action
set is intentionally narrow because deeper CPIs (release_or_mint, lock_or_burn)
require the bridge/mailbox programs to be loaded at the same address and to be
paired with full account wiring — that needs an `anchor_integration` JSON
description which is out of scope for v6.51 round 2.

## Why this strategy matters

Crucible is the project's preferred Solana invariant fuzz engine (per
`AGENTS.md`). The dry-run harness validation now confirms the binary loads and
the harness can run infinitely without a panic — that's the same gate that
unblocks more sophisticated action sets in future rounds.

## What the scaffold does today

`data/security_results/investigations/2026-07-03-lombard-cross-layer/crucible/lombard_token_pool_scaffold/src/main.rs`

| Action | Purpose | Coverage |
|---|---|---|
| `action_type_version` | read-only view; never panics | smoke |
| `action_derive_accounts_release_or_mint` | compute PDA map for release_or_mint account-set; PDAs/stable IDs only | PDA derivation |
| `action_derive_accounts_lock_or_burn` | compute PDA map for lock_or_burn account-set | PDA derivation |

Invariants: `state_pda` and `pool_signer_pda` derived from the canonical
`ccip_tokenpool_config`/`ccip_tokenpool_signer` seeds must remain distinct and
non-default.

## Verification so far

- `crucible run lombard_token_pool invariant_test --dry-run` → **PASS**
  (`- 2 tracked accounts - 1 programs loaded - Single iteration completed
  successfully - Harness validation passed!`).
- `crucible run ... -j 1 --timeout 5` → executes 4 iterations / 0 crashes.

Both captured to `evidence/crucible-token-pool-dry-run-4.log` and
`evidence/crucible-token-pool-stateful-run-5s.log`.

## What is next (carry-forward)

A future pass needs to:

1. Load `bridge.so`, `mailbox.so`, `consortium.so`, `bascule_gmp.so` into the
   Crucible test context with their canonical program IDs, so that CPIs can
   resolve.
2. Type-driven action set built around the actix-action generator:
   `init_global_config(authority=program_upgrade_authority)` →
   `initialize(router, rmn, bridge)` →
   `init_chain_remote_config(remote_chain_selector, mint, cfg, dest_chain_id, dest_caller)` →
   `set_chain_rate_limit(...)` →
   `release_or_mint_tokens(...)` with adversarial payloads
   (wrong destination_caller, decimal mismatch, paused bridge),
   asserting that each adversarial path reverts and that the surrounding
   global state (recipient balance, rate-limit, message_info.status, message_handled)
   stays intact.
3. `action_set_router`, `action_set_rmn`, `action_edit_chain_remote_config`,
   `action_append_remote_pool_addresses`. Each submits either randomly sampled
   or hand-picked fuzzed inputs.
4. The `invariant_test` block checks:
   - `state_pda` ≠ `pool_signer_pda` (always).
   - After a failed release_or_mint, the recipient token balance is unchanged
     (roll-back persistence).
   - After a failed release_or_mint, the mailbox `message_info.status` remains
     `Delivered`.
   - After repeated `init_chain_remote_config` with repeated inputs, the chain
     config PDA matches the deterministically-derived one.

## Honest-zero adjudication

Crucible composite smoke for `lombard_token_pool` does not find any invariant
violation in the 5-second smoke. Deeper stateful exploration is the next
session.

## Files

- `crucible/lombard_token_pool_scaffold/src/main.rs` — three actions +
  invariant test
- `crucible/lombard_token_pool_scaffold/target/deploy/lombard_token_pool.so` —
  mainnet-feature .so (686 KB)
- `evidence/crucible-token-pool-dry-run-4.log` — dry-run captures
- `evidence/crucible-token-pool-stateful-run-5s.log` — 5-second stateful smoke
