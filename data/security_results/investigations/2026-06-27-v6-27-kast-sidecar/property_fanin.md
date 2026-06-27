# KAST / m_ext property fan-in

Date: 2026-06-27  
Target: `m_ext` + `ext_swap`

| Property ID | Surface | Invariant | Bug class | Kill criteria | Evidence required |
|---|---|---|---|---|---|
| `PROP-KAST-001` | variant selection | Exactly one yield feature is active per built image | config / build isolation | source + build matrix confirm no mixed image | built `.so`, IDL diff |
| `PROP-KAST-002` | `scaled-ui::sync` | Gross yield from index update is never negative and is split into `(fees + user distributable)` without minting extra value | precision / conservation | repeated sync cannot increase total claimable value beyond gross delta | pre/post vault balance, fee delta, multiplier delta |
| `PROP-KAST-003` | `scaled-ui::set_fee` + `claim_fees` | fee claim cannot exceed accumulated protocol fee bucket | authorization / accounting | admin-only path cannot drain user yield bucket | token deltas + authority trace |
| `PROP-KAST-004` | `crank::claim_for` | claim amount is bounded by actual pending yield and snapshot ordering cannot double-pay | ordering / accounting | back-to-back claims with stale snapshot do not exceed accrued yield | account deltas, claim snapshots |
| `PROP-KAST-005` | `crank::add_earner/remove_earner/transfer_earner` | earner lifecycle preserves ownership and does not orphan or duplicate pending yield | state machine / stranded funds | transfer+remove cycle cannot create or destroy pending yield beyond known excluded literal | earner PDA state, pending yield totals |
| `PROP-KAST-006` | `crank::add_earn_manager/remove_earn_manager/configure_earn_manager` | manager fee changes are bounded, local, and cannot retroactively rewrite historical user entitlements | retroactive fee / privilege scope | changing fee only affects future claims | fee bucket and claim comparisons |
| `PROP-KAST-007` | Earn CPI boundary | CPI account set must bind to the intended Earn Program, PDAs, and signer scope | CPI validation / account substitution | substituted accounts fail or remain value-neutral | CPI replay trace, program IDs, signer flags |
| `PROP-KAST-008` | wrap/unwrap | extension mint supply and vault M balance remain in sync modulo yield | wrap conservation | wrap→unwrap round trip cannot leak value to caller or admin | token supply, vault balance, user balance |
| `PROP-KAST-009` | admin transfer | pending admin / accept / revoke cannot be raced into unauthorized control takeover | authority transition | only intended pending admin can complete transfer | state flag diff, signer identity |
| `PROP-KAST-010` | migrate path | migration preserves balances and variant metadata without enabling forbidden crank+migrate configuration | migration / layout | migrated state cannot silently switch to a different yield mode | pre/post state layout and variant fields |
| `PROP-KAST-011` | ext_swap | whitelisted swap is 1:1 and cannot unwrap arbitrary extensions or bypass whitelist/global auth | router / whitelist | malformed route cannot mint unsupported extension shares | source/target mint deltas, whitelist PDA |
| `PROP-KAST-012` | cross-variant safety | accounts initialized under one variant cannot be abused under another variant image | image confusion / layout mismatch | incompatible variant/account combos reject or remain value-neutral | instruction logs, account discriminators |
| `PROP-KAST-013` | `scaled-ui::sync` + `claim_fees` | repeated index updates near fractional boundaries cannot accumulate caller- or admin-favorable drift beyond acknowledged dust | precision / repeated-rounding | alternating tiny and medium multiplier jumps cannot create monotonic positive leak to claimant or fee sink | per-step ext index, fee principal, vault collateral delta |
| `PROP-KAST-014` | `crank::sync` + `claim_for` | an earner whose last claim index is ahead of or desynced from the global index cannot be overpaid, permanently frozen, or revived into double-claim by later sync/order changes | ordering / desync / freeze | index regression or stale snapshot must either revert cleanly or preserve future claimability without value creation | earner last_claim fields, global indices, claim attempt trace |
| `PROP-KAST-015` | `crank::configure_earn_manager` + `claim_for` | fee updates are idempotent and prospective only, even when claims, syncs, and manager transfers interleave across different fee schedules | retroactive fee / idempotency | reapplying the same fee or flipping fee schedules around a claim cannot rewrite historical entitlement | pre/post fee bucket, user reward delta, manager fee delta |
| `PROP-KAST-016` | wrap authority + manager authority + Token-2022 extensions | `wrap_authority`, `earn_manager`, `CloseMintAuthority`, and `PermanentDelegate` combinations cannot be composed into an unintended mint/burn/claim control path | authority composition / token-extension abuse | privileged combinations must not broaden authority beyond the intended actor boundary | signer set, extension config, mint/burn/claim deltas |
| `PROP-KAST-017` | bridge accrual vs holder/admin visibility | bridge-side index accrual must equal holder-visible rebasing in `scaled-ui` or explicit admin-claimable surplus in `no-yield`, without silent sink/source creation | yield visibility / conservation | identical M-side accrual cannot disappear from both user-visible balances and admin-claimable state | M vault delta, ext visible supply delta, fee/admin claim delta |

## Execution status

| Property | Executable | Harness coverage |
|---|---|---|
| PROP-KAST-001 | v0 (build matrix) | variant-selection confirmed |
| PROP-KAST-002 | v0 (Crucible scaled-ui) | 23/23 actions, sync/claim active |
| PROP-KAST-003 | v0 (Crucible scaled-ui) | set_fee + claim_fees active |
| PROP-KAST-004 | v0 (Crucible crank) | 23/23 actions, claim_for active |
| PROP-KAST-005 | v0 (Crucible crank) | earner lifecycle tested |
| PROP-KAST-006 | v0 (Crucible crank) | manager config active |
| PROP-KAST-007 | CPI boundary | strategy only |
| PROP-KAST-008 | v0 (Crucible scaled-ui + ext_swap) | wrap/unwrap via both m_ext and ext_swap |
| PROP-KAST-009 | v0 (Crucible all) | admin transfer active |
| PROP-KAST-010 | migrate path | strategy only |
| PROP-KAST-011 | **v0 (Crucible ext_swap + ext_a)** | cross-instance swap from ext_a (no_yield) to primary (scaled-ui) verified; whitelist enforcement confirmed |
| PROP-KAST-012 | cross-variant | strategy only |
| PROP-KAST-013 | v0 (Crucible scaled-ui) | sync + claim_fees executable with Token-2022 mint |
| PROP-KAST-014 | v0 (Crucible crank) | crank sync + claim_for executable with Token-2022 mint |
| PROP-KAST-015 | v0 (Crucible crank) | manager fee + claim interleaving active |
| PROP-KAST-016 | strategy only | Token-2022 extension composition not yet instrumented |
| PROP-KAST-017 | strategy only | bridge accrual visibility not yet instrumented |

## Hard-first hypotheses

1. `H1-scaled-ui-precision`: exploitably asymmetric rounding around multiplier/index boundaries can be chained into repeatable fee theft or user-yield theft
2. `H2-crank-ordering`: stale snapshot or manager fee ordering can double-pay, underflow, or shift pending yield across earners/managers
3. `H3-earner-lifecycle`: `transfer_earner -> remove_earner -> claim_for` can strand or resurrect pending yield
4. `H4-cpi-boundary`: malformed Earn CPI accounts or signer reuse can redirect claims or initialize manager state
5. `H5`: **RETRACTED** — claim_for collateral check is correct for crank mode (see corrected analysis below)
6. `H6-sync-rounding-amplification`: repeated `sync` updates across tiny multiplier changes can amplify rounding into repeatable fee or claimant gain
7. `H7-claim-freeze-desync`: `crank` index regression or stale sync ordering can freeze an earner
8. `H8-fee-retroactivity`: interleaving `configure_earn_manager`, `transfer_earner`, and `claim_for` can retroactively reprice already-accrued yield
9. `H9-authority-extension-composition`: Token-2022 authority extensions plus manager/wrap roles can create a broader mint or claim surface

## Actions (23 total)

| Action | Variants | Status |
|--------|----------|--------|
| transfer_admin | all | active |
| accept_admin | all | active |
| revoke_admin_transfer | all | active |
| add_wrap_authority | all | active |
| remove_wrap_authority | all | active |
| add_earn_manager | crank | active |
| add_earner | crank | active |
| configure_earn_manager | crank | active |
| transfer_earner | crank | active |
| remove_earner | crank | active |
| sync | scaled-ui, crank | active |
| claim_fees | scaled-ui, no-yield | active |
| set_fee | scaled-ui | active |
| claim_for | crank | active |
| claim_for_inflated | crank | active |
| claim_for_big_snapshot | crank | active |
| update_multiplier | scaled-ui, crank | active |
| multisync_claim | crank | active |
| advance_slots | all | active |
| ext_swap_wrap | scaled-ui, crank, no-yield | active (via EXT_SWAP_PROGRAM_ID CPI) |
| ext_swap_unwrap | scaled-ui, crank, no-yield | active (via EXT_SWAP_PROGRAM_ID CPI) |
| ext_swap_swap | scaled-ui, crank, no-yield | active (cross-instance: ext_a -> primary) |
| ext_swap_install | scaled-ui, crank, no-yield | active (adds SwapGlobal as wrap authority) |

## Coverage summary (final campaigns with cross-instance swap)

| Variant | Time | Executions | Edges | Branches | OK ratio | Actions | Crashes |
|---------|------|-----------|-------|----------|----------|---------|---------|
| Scaled-ui (23-act) | 64s | 2,629 | 4,121/25,520 (16.1%) | 3,859/12,760 (30.2%) | 11,150/13,604 (82.0%) | **23/23** | **0** |
| Crank (23-act) | 62s | 2,308 | 4,239/25,844 (16.4%) | 4,016/12,922 (31.1%) | 11,084/18,290 (60.6%) | **23/23** | **0** |

Both variants: **0 crashes, 0 value conservation violations, 0 confirmed defects**. Cross-instance swap (ext_a no_yield -> primary scaled-ui) executes correctly through ext_swap CPI passthrough. Value conservation invariant (`ext_supply * ext_index <= vault_raw * m_index`) holds after sync.

## Freeze analysis (AlreadyClaimed)

**Mechanism**: `earner.last_claim_index >= earn_manager.ext_index` at `claim_for.rs:106` blocks re-claims. After a successful claim, `last_claim_index` is set to `ext_index`, requiring `sync` to advance `ext_index` for the next claim.

**Abuse/griefing vectors examined**:
- **Permanent lock**: Impossible without controlling the earn_authority — `ext_index` advances monotonically, and `sync` is always callable to unfreeze
- **last_claim_index manipulation**: Only settable via `claim_for`, always to current `ext_index`. No external instruction writes to it
- **Earner removal/re-add**: New earner gets `last_claim_index = 1e12` (frozen), cannot exploit existing state
- **ConfigureEarnManager**: Only sets fee parameters, no `ext_index` regression possible
- **Integer overflow**: `u64::MAX` implausibly far (~10^19 claims)

**Verdict**: AlreadyClaimed is a safe, intentional anti-replay mechanism. No griefing/abuse path for non-admin attackers.

---

## Corrected analysis: claim_for collateral check (previously H5)

**Recantation**: The initial claim that `claim_for.rs:137` incorrectly compares raw EXT supply against vault UI M value was WRONG.

**Why the check IS correct**: In crank mode, EXT tokens do not have their own ScaledUiAmount multiplier. They are plain tokens where 1 EXT = 1 current M value unit at minting time. Both sides of the comparison are in current M value units:
- `ext_supply + rewards` = total EXT supply in current M value (each EXT was minted 1:1 with current M value)
- `ext_collateral = vault_raw * m_index / INDEX_SCALE` = vault value in current M value

The check correctly bounds total EXT supply to the vault's current value. An inflated `snapshot_balance` parameter produces larger rewards, but the collateral check caps the total at the vault value — it cannot be bypassed.

**Contrast clarification**: `claim_fees` (scaled-ui variant) uses `principal_to_amount_up(ext_supply, ext_index)` because in scaled-ui mode, the EXT mint HAS a ScaledUiAmount extension that tracks its own multiplier. This is a different variant with different accounting — not a contradiction.

**Lesson**: The crucible variant feature separation (scaled-ui vs crank) creates fundamentally different accounting models. A pattern that looks like a bug in one variant may be correct in the other. Always verify variant context before asserting a finding.
