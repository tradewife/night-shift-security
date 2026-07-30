# Next session queue

**v6.66.0-arbitrum-bold-session3-merkle-p01.** P-01 3/3 PASS. Merkle proof builder ready. **P-08 (bridge freshness — Critical suspicion), P-02/P-03 (cache-spam), P-05/P-06 (OSP soundness)** all still deferred to session 4.

## Priority queue

### 1. Arbitrum/BoLD session 4 (CURRENT — next session)
- **P-08 (CRITICAL SUSPICION)** — bridge/wasmModuleRoot freshness:
  - Build a SmallStep layer-zero edge (requires BigStep-level merkle proof construction extending the existing block-level builder).
  - First, verify `confirmEdgeByOneStepProof` rejects a mismatched `wasmModuleRoot` in `prevConfig`.
  - Then, exercise the `execCtx.bridge` freshness path: change `assertionChain.bridge()` between edge creation and proof submission, verify the proof is rejected or analyze the execution flow for exploitable path.
  - Use `MockOneStepProofEntry.setTamperReturnZero` / `setTamperRevert` for negative controls.
- **P-02/P-03 (cache-spam):** `multiUpdateTimeCacheByChildren` permissionless inflation cannot enable premature `confirmEdgeByTime`.
  - Stateful fuzz over P-02 (direct cache spike on own edge) and P-03 (cross-edge via `updateTimerCacheByClaim`).
- **P-05/P-06 (OSP soundness):** Reject `wasmModuleRoot` mismatch and wrong `machineStep` in inclusion proofs.
- If time permits: P-07, P-09, P-10, P-12.
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
- `sources/arbitrum/bold/repo/contracts/test/foundry/BoLDMocks.sol` (mock contracts + merkle builder)
- `sources/arbitrum/bold/repo/contracts/test/foundry/EdgeChallengeManagerMath.t.sol` (P-11 harness, 7/7 PASS)
- `sources/arbitrum/bold/repo/contracts/test/foundry/EdgeChallengeManagerP01.t.sol` (P-01 harness, 3/3 PASS)
- `sources/arbitrum/bold/repo/contracts/test/foundry/BoLDMerkleProofBuilder.t.sol` (builder self-test, 2/2 PASS)
- `data/security_results/investigations/2026-07-30-arbitrum-bold-deep-dive/{invariants,codegraph}/`
- `data/security_results/lab_notebook/2026-07-30-arbitrum-bold-deep-dive-kickoff.md`
- `data/security_results/lab_notebook/2026-07-30-arbitrum-bold-deep-dive-session2-foundry-math.md`
- `data/security_results/lab_notebook/2026-07-30-arbitrum-bold-deep-dive-session3-merkle-proof-builder-p01.md`
