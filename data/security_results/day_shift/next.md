# Next session queue

**v6.68.1-arbitrum-bold-session5-p13-falsified.** BoLD session 5 complete — Bridge cross-layer probe + P-13 candidate FALSIFIED (prover == WAVM, no divergence). BoLD honest-zero across all surfaces. No Immunefi/Cantina posting. BoLD arc CLOSED.

## Priority queue

### 1. Rotate to next target (HIGH PRIORITY — BoLD arc closed)
- BoLD investigation arc is CLOSED. All 12 property candidates (P-01..P-12) and 8 cross-layer invariants (X-BRIDGE-01..08) resolved honest-zero. P-13 falsified.
- Rotate to next target from rotation queue below.

### 2. Polymarket or Pendle (rotation queue)
- **Polymarket**: Continue from session 2 closeout (honest-zero on PA-01..08, PB-08 unreachable). Either revisit V2 source unlock for deeper static analysis or pivot to protocol-level economic invariants.
- **Pendle**: Fresh target with moderate Cantina rewards. Focus on PT/YT accounting, reward distribution rounding, and SY integration.

### 3. Deferred targets (rotation queue)
| Rank | Target | Notes |
|------|--------|-------|
| 3a | Kamino MEDIUM scope | From day_shift next.md queue |
| 3b | 1inch PROP-023 | From day_shift next.md queue |
| 3c | Flash Trade | From day_shift next.md queue |

### Explicitly do not re-open / already triaged OOS (updated 2026-08-01)
- BoLD dispute protocol + bridge cross-layer — HONEST-ZERO across all surfaces. P-13 FALSIFIED. Arc CLOSED.
- Polymarket — HONEST-ZERO on PA-01..08, PB-08 unreachable
- Makina — X-001 / G-004 / X-004 residual eligibility kills
- 1inch — Already OOS
- marginfi / Flash Trade — Already OOS
- BitGo / Kiln OOS human-gate DO_NOT_SUBMIT
- Invalid/dup: Silo #83293, Origin #82884, OnRe #82764, Superform
- Critical free-mint honest-zeros already closed (lombard, 1inch core, kamino Priority-0, etc.)
- 1inch PROP-023 / Kamino Scope MEDIUM / marginfi T22 / Flash Trade — operator-confirmed not part of current focus

## Local artifacts (not pushed)
- `sources/arbitrum/{nitro,bold,nitro-contracts}/repo/` (gitignored clones)
- `sources/arbitrum/bold/repo/contracts/test/foundry/BoLDMocks.sol` (mock contracts + merkle builder)
- `sources/arbitrum/bold/repo/contracts/test/foundry/EdgeChallengeManagerMath.t.sol` (P-11 harness, 7/7 PASS)
- `sources/arbitrum/bold/repo/contracts/test/foundry/EdgeChallengeManagerP01.t.sol` (P-01 harness, 3/3 PASS)
- `sources/arbitrum/bold/repo/contracts/test/foundry/BoLDMerkleProofBuilder.t.sol` (builder self-test, 2/2 PASS)
- `data/security_results/investigations/2026-07-30-arbitrum-bold-deep-dive/{invariants,codegraph}/`
- `data/security_results/lab_notebook/2026-07-30-arbitrum-bold-deep-dive-kickoff.md`
- `data/security_results/lab_notebook/2026-07-30-arbitrum-bold-deep-dive-session2-foundry-math.md`
- `data/security_results/lab_notebook/2026-07-30-arbitrum-bold-deep-dive-session3-merkle-proof-builder-p01.md`
