# STRAT-S6 — Multi-program Crucible scaffold (R1 outcome)

## Round metadata
| Field | Value |
|------|-------|
| Round | v6.51.6 (R1 of the carry-forward agenda) |
| Skill invocation order | `ultrafuzz-discovery` (refresh `setup.md`/`property_fanin.md`) -> `agentic-strategy-generation` (4 strategies, >=70% primary) -> `fuzz-scaffolder` (handoff) -> executable attempts -> preservation -> `ultrafuzz-discovery` adjudication |
| Primary subsystem | Solana `lombard_token_pool` + cross-layer (bridge/mailbox/consortium/bascule_gmp/bascule/mock_ccip_offramp/mailbox_receiver) |
| Evidence threshold | STRICT CPCV / credible-harness |

## Goal

Load all six companion programs (`bridge`, `mailbox`, `consortium`,
`bascule_gmp`, `bascule`, `mock_ccip_offramp`) into the same Crucible
`TestContext` as `lombard_token_pool` so that follow-up rounds (R2
adversarial CPIs, R5 CSI "post_session_signatures" probe) can drive
multi-program actions from a single shared context without losing
state.

## Outcome

Dry-run PASS with **8 programs loaded, 2 tracked accounts**, harness
validation succeeded. 5/5 actions discovered in 8-second stateful smoke.
21,076 iterations / 0 crashes / 0 invariant violations.

## Action set (v6.51.6)

| Action | Source |
|--------|--------|
| `action_type_version` | `lombard_token_pool::TypeVersion` view |
| `action_derive_accounts_release_or_mint` | `lombard_token_pool::DeriveAccountsReleaseOrMintTokens` Compute stage with arbitrary `ReleaseOrMintInV1` |
| `action_derive_accounts_lock_or_burn` | `lombard_token_pool::DeriveAccountsLockOrBurnTokens` Compute stage with arbitrary `LockOrBurnInV1` |
| `action_bootstrap_multi_program` | Re-runs the view-only smoke after multi-program load (proves cache-hot program ID slots) |
| `action_config_pda_uniqueness_check` | Pure compute: re-derives `state_pda` and `pool_signer_pda` from the fixture mint, asserts they are stable across iterations |

## Invariants (v6.51.6)

| Invariant | Mechanism |
|-----------|-----------|
| `state_pda != default` | `fuzz_assert_ne!` |
| `pool_signer_pda != default` | `fuzz_assert_ne!` |
| `state_pda != pool_signer_pda` | `fuzz_assert_ne!` (seeds differ: `ccip_tokenpool_config` vs `ccip_tokenpool_signer`) |
| All 8 program IDs mutually distinct | `fuzz_assert_ne!` pairwise |
| `lombard_token_pool_id != mint/admin` | sentinel `fuzz_assert_ne!` |

## Carry-forward for R2

CPI integration of `release_or_mint_tokens` with bridge and mailbox
programs. That requires:

1. Consortiumn instance hydration (admin + initial valset PDA).
2. Bridge instance hydration (`gmp_send_message`, rate limit, msg_pda).
3. Mailbox instance hydration (`outbound_message_path`,
   `gmp_receive`, `handled` PDA).
4. Token-pool `state` PDA + `pool_signer` PDA hydration.
5. Mirror Call integration via `ctx.program(...).call(...).invoke(...)`.

That is a multi-investigation carry-forward, not a single round.

## Provenance

- Source review: `sources/lombard-finance/repo/programs/{lombard_token_pool,consortium,bridge,mailbox,bascule_gmp,bascule,mock_ccip_offramp,mailbox_receiver}/`.
- IDL source: `sources/lombard-finance/repo/target/idl/*.json` (committed; stamped under scaffold `idls/`).
- Hard binary source: `sources/lombard-finance/repo/target/deploy/*.so` (committed; copied into scaffold `target/deploy/`).
- Crucible harness pattern: `sources/crucible/repo/examples/escrow/fuzz/escrow/` and `sources/crucible/repo/examples/staking/fuzz/staking/`.
