# Session plan — current

**Status: CLOSED (2026-08-01 session 5 continuation).** Arbitrum/BoLD cross-layer Bridge↔SequencerInbox↔Outbox↔Rollup deep probe — P-13 FALSIFIED. **`submit_ready=0`** (no bug exists). No Immunefi/Cantina posts this session.

## Session 5 closeout summary

### Arbitrum/BoLD session 5 — Bridge cross-layer deep probe + P-13 falsification (2026-08-01)
- **Scope shift:** Pivoted from BoLD dispute protocol to Bridge↔SequencerInbox↔Outbox↔Rollup cross-layer interactions per `next.md` hint.
- **8 cross-layer invariants traced (X-BRIDGE-01, X-SEQ-01, X-OUTBOX-01, X-UPGRADE-01/02, X-DEEP-01..05):**
  - Bridge accumulator integrity: admin-gated, Held.
  - `sequencerReportedSubMessageCount` first-batch bypass: admin-gated.
  - MerkleLib.calculateRoot index check: not exploitable due to bounded `machineStep`.
  - BOLDUpgradeAction loop-bound mutation: admin-gated.
  - BOLDUpgradeAction createConfig preimage DOS: admin-triggered.
  - **`executeSelect` type-mismatch (X-DEEP-01): FALSIFIED on continuation.**
- **P-13 falsification:**
  - `OneStepProver0.executeSelect` does NOT enforce WASM spec type-match rule — TRUE.
  - Real WASM runtimes trap on `select(a:I32, b:I64, c:I32)` — **FALSE**. Production WAVM runtime (`machine.rs:2328`) also skips a/b type check, matching the prover.
  - `wasmparser::Validator` (`binary.rs:343`) enforces WASM spec type rules at module-load time, upstream of both the WAVM runtime and the Solidity prover. No valid WASM module can contain a type-mismatched select instruction.
  - **Severity: NOT A BUG.** Prover and WAVM runtime are in lockstep. The invariant is preserved by upstream validation, not runtime/prover checks.
- **Test artifacts:** `OneStepProverSelectTypeMismatchP13.t.sol` (5/5 PASS), `P13FalsificationAdjudication.t.sol` (3/3 PASS NEW).
- **Lab notebook:** `lab_notebook/2026-08-01-arbitrum-bold-session5-bridge-crosslayer.md`.
- **Investigation workspace:** `investigations/2026-08-01-arbitrum-bold-session5-bridge-crosslayer/`.

### Conclusion: **P-13 FALSIFIED (prover == WAVM, no divergence). BoLD session 5: HONEST-ZERO across ALL surfaces.**
- The P-13 candidate was falsified by deep source-level analysis of the production WAVM runtime and the wasmparser validation gate.
- No end-to-end PoC needed because no bug exists.
- BoLD investigation arc: CLOSED. Rotate to next target.

## Hard rules retained
- No external post without human-gate PASS.
- Eligibility triad mandatory for residual claims.
- Investigations / lab notebooks local unless operator explicitly publishes.
- Do NOT re-open Polymarket / Makina / Kamino / 1inch / marginfi / Flash Trade — all OOS.

## Night Shift handoff
- Arbitrum/BoLD arc CLOSED — honest-zero across all 12 property candidates + 8 cross-layer invariants. P-13 falsified.
- Do NOT re-open BoLD without new deployed code or scope update.
- Do NOT re-open Polymarket without new deployed code or scope update.
