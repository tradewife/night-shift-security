# Self-Criticism — What Hasn't Worked (2026-06-20)

This document records attack surfaces and approaches that have been tried but have NOT produced submittable bugs. It is updated after every run to prevent duplicate effort and to identify blind spots.

## Audited Protocols and Surfaces Tried

### Kamino KLend (sources/kamino/klend/)
- **Price manipulation**: Tried oracle staleness borrow probe — `ReserveStale` error blocks it. Blocked.
- **Flash loans**: Tried flash loan collateral loop — atomic, no exploit. Blocked.
- **Reentrancy**: Confirmed no cross-function reentrancy via obligation refresh.
- **Integer overflow**: Confirmed `compound_interest` uses `FullMath.mulDiv` (safe). No overflow.
- **Access control**: Confirmed all admin instructions are properly gated.
- **Borrow checks**: `check_borrow_possible` requires `ALL_CHECKS` price status. Blocked by stale Scope oracle on fork.

### Uniswap v4 (sources/uniswap_v4/repo/)
- **Hook delta extraction (afterSwap)**: Confirmed bounded by `swapDelta - hookDelta` (Hooks.sol:312). Design feature.
- **VULN-001 mint() unchecked overflow**: **FALSIFIED** by `SafeCast.toInt128(uint256)` at SafeCast.sol:56-59.
- **Sync/settle/take**: `sync` has no access control but is harmless (resets transient storage per tx).
- **Donate**: Donor always pays (credit offset by actual token transfer).
- **Protocol fees**: `setProtocolFee` and `collectProtocolFees` are gated on `protocolFeeController`.
- **mint/burn ERC6909**: No unbacked claim token minting possible.
- **PoolManager USDC balance**: $56.9M tracked. High-value target but no exploit path.

### Aave v3 (sources/aave_v3/repo/)
- **Flash loan callback**: Properly designed with `validation → user payload → cache → updateState` flow.
- **Liquidation bonus**: Properly bounded by `closeFactor` and `liquidationBonus`.
- **Isolation mode debt ceiling**: Properly enforced.
- **eMode**: Complex but properly bounded by category configuration.
- **Stable rate mode**: Interest calculations are deterministic and bounded.

### Raydium CLMM (sources/raydium/repo/)
- **Tick array bitmap**: Proper boundary handling for negative/positive ticks.
- **AMM math**: Standard Uniswap V3 concentrated liquidity math. Well-tested.
- **Reward distribution**: Rounding errors are <1 lamport. Not exploitable.

### Wormhole (sources/wormhole/repo/)
- **Already-completed VAA replay**: `BRIDGE_ACCOUNTING_VIOLATION:0`. No impact.
- **Mocked authorization**: `HARNESS_AUTH_MOCKED=1` is a hard non-submittable marker.
- **Asset metadata**: Same-chain metadata skips before `createWrapped`. No impact.
- **Paged corpus scan**: 718 VAAs, all authorized replay only.

### Orca Whirlpools (sources/orca/repo/)
- **next_protocol_fee wrapping_add**: Theoretical issue, practically infeasible (requires ~1.8e19 swaps).
- **migrate_repurpose_reward_authority_space**: Missing access control but one-time migration, no fund loss.
- **decrease_liquidity v2 event**: Minor doc issue, emits pre-fee amount.
- **Token-2022 transfer fees**: Properly handled by SPL token-2022 program.
- **Concentrated liquidity math**: Standard Uniswap V3 math. Well-tested.

### Jito (sources/jito/repo/)
- **N/A**: Infrastructure (validator history, steward). Not DeFi.

### Morpho Blue (sources/morpho/repo/)
- **N/A**: `harness_built`, not `ready`. USDC/WETH market has no positions on mainnet.

## Universal Attack Surfaces — Status

| Surface | Tried On | Result |
|---------|----------|--------|
| Price manipulation | KLend, UniV4, Aave v3 | All defended (stale checks, oracle bounds) |
| Flash loan attacks | KLend, UniV4, Aave v3 | All defended (atomic, proper callbacks) |
| Reentrancy | KLend, UniV4, Aave v3, Orca | All defended (locks, state checks) |
| Integer overflow | UniV4, Orca | FALSIFIED (SafeCast) or practically infeasible (Orca) |
| Access control | All | All defended (proper role checks) |
| Callback manipulation | Aave v3, UniV4 | All defended (proper state ordering) |
| Signature replay | Wormhole | All defended (nonces, guardian checks) |
| Liquidation | Aave v3 | Defended (close factor, bonus bounds) |
| Reward distribution | Raydium, Orca | Defended (rounding < 1 lamport) |
| Token integration | UniV4, Orca | Defended (token-2022 extensions handled) |

## Blind Spots — What Hasn't Been Tried

1. **Reserve Protocol** ($10M Cantina) — not yet onboarded
2. **Coinbase** ($5M Cantina) — not yet onboarded
3. **Ethena** ($3M Immunefi) — not yet onboarded
4. **SSV Network** ($250K Immunefi) — not yet onboarded
5. **Pendle** ($2M Cantina) — not yet onboarded
6. **DeXe Protocol** ($500K Immunefi) — not yet onboarded

## Lesson Learned: Library Override Pattern

**Pattern:** Many "vulnerabilities" that look like unchecked integer overflows are protected by upstream library overrides.

**Verification step for any unchecked-conversion claim:**
1. Find the `using <Library> for *;` declaration
2. Find the actual library function for the conversion
3. Verify the library function has explicit revert
4. Write a Foundry test to confirm

**Example:** VULN-001 claimed `PoolManager.mint()` unchecked `amount.toInt128()` is exploitable. False positive because `SafeCast.toInt128(uint256)` at SafeCast.sol:56-59 explicitly reverts for `x >= 1 << 127`.

## What to Try Next (v6)

1. **Onboard Reserve Protocol** — $10M bounty, complex RToken mechanism
2. **Onboard Coinbase** — $5M bounty, exchange code
3. **Onboard Ethena** — $3M bounty, synthetic dollar with novel attack surface
4. **Focus on less-audited, newer programs** where novel bugs are more likely
5. **Use different attack classes** — configuration errors, integration bugs, governance attacks

## Recommended Reading for Next Agent

1. **SPEC.md** — v6 spec with target rotation strategy
2. **foundry/test/UniV4MintOverflowFalsification.t.sol** — VULN-001 falsification (must read)
3. **foundry/test/OrcaProtocolFeeWrapping.t.sol** — Orca wrapping analysis
4. **tests/test_uniswap_v4_hook_probe.py** — Uniswap v4 hook tests
5. **tests/test_orca_wrapping.py** — Orca wrapping tests
6. **AUDIT.md** — current audit log with all findings (including falsified VULN-001)
7. **data/security_results/lab_notebook/** — full history of all runs
