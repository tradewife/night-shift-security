# STRAT-S6 — Adversarial release_or_mint action set (R2 outcome)

## Round metadata
| Field | Value |
|------|-------|
| Round | v6.51.6 (R2 carry-forward: full-repo Cargo unit-test recap; next CPI integration blocked on upgrade-authority plumbing) |
| Skill invocation | `ultrafuzz-discovery` |
| Primary subsystem | Luna-lombard_token_pool melee-adjacent functions + cross-program signature authoring |

## Goal

Try to drive the **release_or_mint_tokens** instruction end-to-end through a
multi-program Crucible context (consortium initialize, mailbox initialize,
bridge initialize, then release_or_mint succeed and revert).

## Outcome: ENG-BLOCKED but progressed via unit-test recap

`lombard_token_pool::initialize`, `init_global_config`, and `consortium::initialize`
all require the program's upgrade authority as signer. Crucible
`TestContext::add_program` does NOT expose a hook to set the
`bpf_loader_upgradeable` `program_data.upgrade_authority_address`. The
required signature cannot be synthesised from a fresh `Keypair`.

Therefore R2 was **re-scoped** to the unit-test recap that was promised at
the end of session-7b and to adding extra surface coverage that does NOT
require the upgrade authority (the `DeriveAccounts*` and `TypeVersion`
actions, plus a brand-new `MalformedAttestationData`-style argument sweep).

## Unit test recap (`SOURCE-LOMBARD`)

The full lombard-finance workspace contains **19 unit test crates**.
v6.51.6 documentation pass:

| Crate | Unit tests |
|-------|------------|
| abi_utils | 7 |
| arrayvec | 3 |
| asset_router | 4 |
| bascule | 1 |
| bascule_gmp | 2 |
| base_token_pool | 8 |
| bridge | 1 |
| build_commit | 1 |
| ccip_common | 7 |
| consortium | 7 (includes the index-bounds DoS probe from v6.51.5) |
| lbtc | 14 |
| lombard_token_pool | 2 |
| mailbox | 5 |
| mailbox_receiver | 1 |
| mock_ccip_offramp | 1 |
| mock_ccip_rmn | 1 |
| ratio_oracle | 1 |
| registry | 1 |
| rmn_remote | 1 |
| **Total** | **68 passing** |

Captured at `evidence/full-cargo-test-v651-recap.log`.

## R3 carry-forward (validator/bankrun)

Validation that **does not need upgrade authority** can be done in
`BankrunProvider`. R3 build target:
`sources/lombard-finance/repo/tests/lombard_cross_layer_v651_release_or_mint_rollback.bankrun.ts`
— using the validator's built-in upgrade-authority for the localnet cluster
to call `init_global_config` once, then drive `init_chain_remote_config`
and `release_or_mint_tokens` end-to-end.

## Honest-zero recording

Round-2 result: honest-zero for fund-loss on the release_or_mint happy
path under Crucible (no testable CP path because of the upgrade-authority
gating). The RLS Ced oil emulation is still the next responsible step
(R3 / validator / bankrun).

## Provenance

- Source: `sources/lombard-finance/repo/programs/*`.
- Unit tests: `sources/lombard-finance/repo/programs/*/src/with_some_unit_tests.rs` (per-crate).
- Crucible harness pattern: `sources/crucible/repo/crates/crucible-test-context/src/lib.rs` (read-only review of `add_program` API).
