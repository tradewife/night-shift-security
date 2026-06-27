# Lab entry — 2026-06-27

## Trigger
Manual: Enzyme Onyx (Immunefi) fresh-target deep-dive handoff from session orchestration.

## Investigated
- **Target**: Enzyme Onyx — EVM modular tokenization protocol (Shares, Valuation, Fees, Queues, Forwarders, CCIP)
- **Repo**: `sources/onyx/repo` (github.com/enzymefinance/protocol-onyx)
- **Scope**: Full In-Scope contract set from Immunefi bounty page (Shares, ValuationHandler, FeeHandler, ContinuousFlatRate*FeeTrackers, LinearCreditDebtTracker, AccountERC20Tracker, ERC7540Like*Queues, Limited/OpenAccessForwarders, StorageHelpersLib, OneToOneAggregator)
- **Audits**: ChainSecurity (Sep 2025) + CCIP audit (May 2026) in-repo

## Depth

### Code intelligence
- Read all 25+ contracts in src/ fully (core plus peripherals)
- Analyzed all 21 Foundry test files, 21 harnesses, mocks, and utility libraries
- Built integration test suite (7 PoC tests) exercising: fee cycles, queue execution, perf fee HWM reset on zero supply, phantom fee with LinearCreditDebtTracker, entrance fee rounding bypass, management fee retroactive rate change, fee claim solvency
- Built fuzz tests (2 invariant tests, 256 runs each): solvency consistency across random deposit/fee/time parameters, multi-cycle accounting

### Test results
- **7/7 integration PoC tests passing** — core flow invariants hold
- **512/512 fuzz runs passing** — no solvency violation or phantom fee under random parameters
- **Build**: `forge build` clean with 192 artifacts
- **Fork tests**: Not run (no RPC endpoint configured in repo foundry.toml)

### Attack surface covered
| Hypothesis | Result | Notes |
|---|---|---|
| Fee double-counting on sequential updateShareValue | HONEST-ZERO | HWM prevents perf fee double-charge; management fee netValue correctly deducts prior fees |
| Stale share price via deposit queue (no staleness check) | DESIGN CHOICE | Documented; SyncDepositHandler has staleness check, ERC7540 queues don't |
| Entrance/exit fee rounding bypass for tiny amounts | DESIGN CHOICE | Scoped as "small-amount rounding DoS" — excluded by bounty rules |
| LinearCreditDebtTracker + AccountERC20Tracker double-counting | ADMIN ERROR | Not a protocol bug; admin manages tracker composition |
| Retroactive mgmt fee rate change | DESIGN CHOICE | Documented: "Updating rate will apply the new rate on any time since last settlement" |
| Phantom perf fee on pre-existing tracker value | ADMIN ACCOUNTING | LinearCreditDebtTracker must be kept in sync with actual asset positions |
| Queue duplicate execution | SAFE | Deleted request returns zeros, ZeroShares guard prevents mint |
| Forwarder access escalation | BY DESIGN | Open/Limited access is intentional admin delegation |
| CCIP wallet reentrancy via processMessageData | SAFE | Self-call only, wallet has no special Shares permissions |
| claimFees front-running updateShareValue | SAFE | Both execute atomically within same tx; no reentrancy path |
| TotalValue < totalFeesOwed underflow in settleDynamicFees | SAFE | Reverts transitively — admin prevented from insolvent updates |

### No submit_ready candidates

No exploitable bugs were identified after rigorous analysis of the primary subsystem (ValuationHandler + FeeHandler + Trackers + Queues + Forwarders cross-contract interactions). All state mutators are admin-gated or have explicit access controls. The delegated trust model (admin has broad powers) means admin-triggerable issues are out of scope unless they affect user funds in unexpected ways.

**Honest-zero outcome** on the three most promising hypotheses:
1. Fee accounting inconsistency across deposit/update/redeem cycles (fuzz 256 runs) — invariant holds
2. Phantom performance fee charging on admin-managed tracker value — tested empirically, accounting is correct (HWM resets on zero supply, no phantom charge)
3. Queue + share value cross-component state corruption — all sequenced operations preserve solvency

## Surfaces not yet saturated (defer)

- **OneToOneAggregator**: Hardcoded 1.0 aggregator — if integrated as canonical oracle, trivial to manipulate. But no on-chain integration path exists (used as Chainlink compat layer; admin must deploy and set manually).
- **DepositorWallet / WalletsManager / CCIP**: Cross-chain flows depend on CCIP router integration and are gated by admin. The `batchSendTokensViaCCIP` refund pattern is correct (`remaining balance → msg.sender`).
- **AddressListsSharesTransferValidator**: Access control lists for share transfers — admin configurable, no bypass found.

## Night Shift handoff

- **Cron OK to run**: `nss-hipif-chain` can proceed normally. Onyx not in cron scope.
- **Cron skip**: Onyx EVM target — not in Night Shift hunt slugs (Solana-focused HIPIF chain).
- **Open questions**: None. Target is well-instrumented but yields honest-zero on the modeled attack surfaces. Fresh target per spec; not yet listed in `knowledge/concrete_candidates.jsonl`.

## Next action
Close target. Move to next high-value EVM target in rotation, or re-evaluate if Onyx scope expands materially (new contract additions, upgrade).

## Key files
- Integration PoC: `sources/onyx/repo/test/contracts/OnyxIntegrationPoC.t.sol` (7 tests, all pass)
- Fuzz tests: `sources/onyx/repo/test/contracts/OnyxFuzz.t.sol` (2 tests, 256 runs each, all pass)
- Build verified: `forge build` clean, `forge test` passes all suites including protocol tests
