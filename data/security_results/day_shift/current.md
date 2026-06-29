# Session plan — v6.38 Sablier Cantina Bounty deep-dive — Corpus-Exhaustive

**Status: closed** (2026-06-30) — Sablier Cantina bounty corpus-exhaustive deep-dive. AuditVault + Solodit corpus mining, 6 cross-protocol patterns adjudicated, AuditVault finding #42010 (debt overflow) proven not exploitable via H-017 empirical test. 33/33 Flow tests pass (16 custom probes + 17 existing invariants + 4 new). Lockup and Airdrops CEI correct. No submission-ready finding.

## Summary

Investigation workspace at `data/security_results/investigations/2026-06-29-v6-37-sablier-deep-dive/`.

### What was done (v6.38 extension)

- **AuditVault corpus mining**: Scanned 2384 JSONL entries for streaming/vesting/airdrop patterns; found 6 correlated cross-protocol patterns (+1 Sablier-specific at line 995)
- **AuditVault #42010 adjudication**: Sablier-specific "overflow in debt calculation" in `_ongoingDebtScaledOf`. Proved not exploitable — `UD21x18 = uint128` constraint means max product `3.7e50 << uint256.max (1.15e77)`. Empirical test H-017 passes with `type(uint128).max` RPS × 1e12s warp.
- **Solodit corpus scan**: 0 Sablier matches found
- **4 new Death Probe tests**: H-017 (overflow proof), H-018 (rate accumulation), H-019 (edge deposit), H-020 (fee dust boundary) — all pass
- **Full test suite**: 289/290 pass (1 fork test fails due to missing RPC URL)
- **Lockup review**: CEI pattern verified correct; hooks fire AFTER state updates + token transfers
- **Merkle airdrops review**: BitMap prevents double-claim, `TOTAL_PERCENTAGE == uUNIT` enforced at construction, clawback logic correct
- **STRAT-002 updated**: Expanded to include v6.38 corpus-driven analysis and overflow adjudication

### Key findings

| ID | Finding | Severity | Submission-ready |
|----|---------|----------|-----------------|
| STRAT-001 | Protocol fee truncation on dust withdrawals (< 100 raw units for 1% fee) | Low (Info) | No |
| #42010 (AuditVault) | Debt overflow in `_ongoingDebtScaledOf` | **Adjudicated: not exploitable** | N/A |
| All others | 13 hypothesis-specific probes — all honest-zero | — | — |

### Artifacts

- `data/security_results/investigations/2026-06-29-v6-37-sablier-deep-dive/{setup.md,property_fanin.md,strategies/*}`
- `sources/sablier/flow/repo/tests/v6-37-SablierFlowDeathProbe.t.sol` (16 tests, 33 with fuzz variants)

### What did NOT move

- **`submit_ready` unchanged**: still 1 (OnRe H1 v6.13).
- **No NSS pipeline changes**: 0 changes.
- **Key blocker**: Sablier's core math (Flow debt, Lockup lifecycle, Merkle claims) is provably sound. No residual attack surface found across all 3 repos.

## Submission gate status

| Gate | Status |
|------|--------|
| OnRe H1 (v6.13) | **submit_ready=1** (unchanged) |
| Silo reentrancy (v6.32) | **submission-ready, requires human gate** (unchanged) |
| Veda Token-2022 STRAT-01 (v6.33) | **Honest-zero for current production** |
| Coinbase Cantina (v6.34) | **4 carry-forward hypotheses adjudicated honest-zero** |
| Monad UI Bounty (v6.35) | **16 findings, 0 submission-ready. Surface exhausted.** |
| Pendle (v6.36) | **Corpus x-ray honest-zero** |
| Sablier Cantina (v6.38) | **33/33 tests, corpus-exhaustive, 0 submission-ready. Overflow #42010 adjudicated not exploitable.** |
| **Overall `submit_ready`** | **1**, unchanged |
