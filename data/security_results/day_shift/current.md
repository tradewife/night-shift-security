# Session plan — current

**Status: closed honest-zero (2026-07-07). Metric OMM Sherlock #1279 v6.54 session complete — L-29 bug confirmed, withheld as prior-ACK. Pivot needed.**

## Active arc: Metric OMM Sherlock Contest #1279 (v6.54)

**Contest:** `audits.sherlock.xyz/contests/1279`, $150K USDC, 2026-07-06 → 2026-07-27
**Repo:** `sherlock-audit/2026-07-metric-tradewife` (public snapshot `2e4e866`; audit commits `7b9ab56`/`d210a84`/`056c204` private)
**Workspace (kept-local, gitignored):** `data/security_results/investigations/2026-07-07-metric-omm-sherlock-1279/`

### Results — 10 strategies, 29 test variants, 437 tests pass

| Strategy | Variants | Result |
|----------|----------|--------|
| SEQ-01 Velocity guard (PriceVelocityGuardExtension) | 5/5 | Correct behavior |
| SEQ-02/03 Multihop rounding (SwapMath) | 4/4 | Bounded, no escape |
| SEQ-04 Provider staleness (ProtectedPriceProviderL2) | 5/5 | Correct fail-closed |
| SEQ-05 Blacklist compose (OracleBase.register) | 3/3 | **Bug confirmed — L-29 (withheld)** |
| SEQ-06 Extension toggle (OracleValueStopLossExtension) | 3/3 | Correct behavior |
| SEQ-07 Pause liveness | 3/3 | Correct behavior |
| ECON-01 Full lifecycle (deposit→swap→withdraw) | 3/3 | No insolvency |
| ECON-02 Stop-loss extension drawdown | 3/3 | Correct behavior |
| H1 AnchoredPriceProvider band math (protocol-owned) | 63 + fuzz | Honest-zero |
| H2 SwapMath rounding amplification | 1000-run fuzz | Honest-zero |

### L-29 (`OracleBase.register()` clears admin blacklist) — confirmed, NOT submitted

- PoC: `2026-07-metric-tradewife/smart-contracts-poc/test/StratRegisterBlacklist.t.sol` (3 tests, all PASS).
- Reproduction: any caller can `register{value: 1 wei}(feedId, pool, factory)` to clear `blacklisted[pool]=false`. Replayable indefinitely.
- **Why withheld:**
  1. The May collaborative audit (`2026-07-06_Metric-Collaborative_Audit_Report.pdf` p.99) lists the same code as **L-29 [ACKNOWLEDGED, won't fix]**, source `sherlock-audit/2026-05-metric-may-22nd/issues/124`. The contest README links this PDF.
  2. Sherlock guideline VII.16 invalidates issues from prior audits (linked in the contest README) marked ACK/unfixed.
  3. The contest README declares `Oracle ADMIN_ROLE` **trusted** for blacklist/integrators/factories/registration fee/withdrawEth.
  4. The prior audit's own impact assessment: "Operational control only — no funds are at risk." No isolated loss-of-funds path; theoretical impact requires a *separate* pool compromise.
- **Decision: do NOT file on GitHub.** Filing risks a public-record invalid and reputation hit with Lead Judge (`gh0xt`) and Senior Watson (`pkqs90`).

### Other leads eliminated

- H4 sequencer: `ProtectedPriceProviderL2` is a full post-Zellic rewrite with no sequencer-uptime code at all. Stale-duplicate/dead.
- exactOutput callback reentry: protected by transient callback context, `FACTORY.isPool` validation, `_requireExpectedCallbackCaller`, and mutable transient per-hop context. Low EV.
- Price manipulation via `OracleValueStopLoss`: extension computes drawdown post-swap, so swap rebalances bin before the check. Working as designed.
- AnchoredPriceProvider band math: 75-test protocol-owned suite (PR#58 harmonic-mean rework) + our SEQ-04. Honest-zero on the primary hypothesis.

### Caveat (carried forward)

Public fork snapshot is commit `2e4e866`; contest README pins private commits `7b9ab56`/`d210a84`/`056c204` (inaccessible without contest team membership). Disposition of all 10 hypotheses is robust to this delta, but if a re-open is justified, exact-audit-tree re-verify is the first move.

### Next: pivot to new target

`submit_ready` unchanged (0). Candidates: any fresh operator-selected Cantina/Immunefi slug. The router-callback-allowance drain noted in the collaborative report (H-1) is not in the ACK list and may be worth follow-up if Metric OMM is re-opened; otherwise pivot.

## Completed arc: Euler v2 Cantina (closed scope-blocked, v6.53.1)

H4/PROP-EV2-004 FoT accounting desync confirmed technically (11 tests: 7 local + 4 fork) but **out of scope** per Cantina "weird tokens" + "EulerRouter misconfiguration" exclusions. Fork-verified propagates through real EulerRouter on mainnet. `submit_ready` unchanged (0). **Do not reopen** without scope changes.

## Completed arc: LI.FI Diamond routing (closed scope-blocked, v6.51.23)

23/23 tests passing. EXECUTOR-ALLOWLIST-BYPASS confirmed but scope-blocked by Self-Crafted Calldata Risks. PROP-LIFI-C1 owner-only, excluded by Centralization By Design. Value conservation honest-zero. **Do not reopen** without bounty scope changes.

## Completed arc: Polymarket Cantina (closed honest-zero, v6.51.21)

51/51 tests passing, 14 hypotheses tested, all disproven or Low-Medium severity. Only finding: overflow DoS at `Trading.sol:654` — real but marginal. **Do not reopen** without new scope.

## Completed arc: Lombard cross-layer (closed acceptable-with-gaps, v6.51.19)

Substrate-confirmed honest-zeros (R1 rollback, R2 PDA collision, R3 Rust probes) + 1 round-level engineering_blocker. PROP-EVM-MBOX-005 deferred (Hardhat fork needed). **Do not reopen** without new scope / Hardhat fork substrate.

## Completed arc: Symbiotic Cantina (closed honest-zero, v6.51.22)

50+ contracts analyzed, 6 audits cross-checked, all fuzz harnesses pass. BurnerRouter no-access-control: confirmed via 9 PoC tests but no net profit path. **Do not reopen** without new scope.
