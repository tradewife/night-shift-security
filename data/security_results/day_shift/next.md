# Next session queue

**v6.65.0 ACTIVE.** Arbitrum/BoLD deep-dive session 1 (kickoff) closed. Structural analysis complete: 12 contracts read, 32 invariants cataloged, 12 property candidates (P-01..P-12) written. **CRITICAL SUSPICION: P-08** (`confirmEdgeByOneStepProof` reads `assertionChain.bridge()` fresh each call; `ConfigData` does NOT capture bridge). Foundry harness must be built from scratch — BoLD ships zero Foundry tests for `EdgeChallengeManager`.

## Priority queue

### 1. Arbitrum/BoLD session 2 (CURRENT — next session)
- Build `MockAssertionChain` + `MockOneStepProofEntry` + minimal `EdgeChallengeManagerHarness.t.sol` for P-01..P-08 first wave.
- Targets: P-01 honest-wins-by-time (positive control), P-02/P-03/P-04 cache-spam non-shortcut, P-05/P-06 OSP soundness, P-08 bridge/wasm freshness (critical suspicion).
- Defer Go end-to-end until Foundry surface is honest-zero.
- All artifacts local per AGENTS.md keep-local rules.

### 2. Defer until BoLD honest-zero on Foundry surface
| Rank | Action |
|------|--------|
| 2a | Go end-to-end harness (nitro-testnode + bold testing/endtoend) for cross-process verification |
| 2b | Stylus runtime / WASM proof integration edge cases |
| 2c | Bridge/gateway + fast-withdrawal paths interacting with delayed or challenged assertions |
| 2d | Economic / griefing vectors that escalate to High |

### Explicitly do not re-open / already triaged OOS
- Polymarket PA-01..08 honest-zero (vendor + sessions 2-4)
- Polymarket PB-08 unreachable on 0.8.34
- Makina X-001 / G-004 / X-004 residual eligibility kills
- BitGo / Kiln OOS human-gate DO_NOT_SUBMIT
- Invalid/dup: Silo #83293, Origin #82884, OnRe #82764, Superform
- Critical free-mint honest-zeros already closed (lombard, 1inch core, kamino Priority-0, etc.)
- 1inch PROP-023 / Kamino Scope MEDIUM / marginfi T22 / Flash Trade — operator-confirmed not part of current focus

## Local artifacts (not pushed)
- `sources/arbitrum/{nitro,bold,nitro-contracts}/repo/` (gitignored clones)
- `data/security_results/investigations/2026-07-30-arbitrum-bold-deep-dive/{invariants,codegraph}/`
- `data/security_results/lab_notebook/2026-07-30-arbitrum-bold-deep-dive-kickoff.md`
- `sources/polymarket/ctf-exchange-v2/src/test/V2CombinatorialInvariant.t.sol` (9 tests, 9/9 PASS)
- `data/security_results/investigations/2026-07-29-polymarket-cantina/`
- `data/security_results/lab_notebook/2026-07-30-polymarket-cantina-session4-continuation.md`
