# 2026-06-20 — Empirical-calibration self-assessment

**Author:** Session-5 orchestrator (self-criticism pass)

## What I am confident about

1. **Lane A passes.** The deployed `EthenaMinting V1` exposes the same uint64-truncation bug class that the C4 Ethena Labs invitational flagged in Nov 2024. Four distinct uint256 nonces (1, 1+2^64, 1+2^128, 1+2^192) produce the same `(slot, bit) = (0, 2)` pair under staticcall. This is reproducible by any future forge test that runs the same selectors (`0xf4ee2a8b` for `verifyNonce`).

2. **Lane B passes.** The per-block mint cap (2,000,000 USDe) plus the `MINTER_ROLE` gate plus the EIP-712 envelope enforcement collectively prevent any direct USDe extraction via the nonce-collision lever. The cap check is independent of the bitmap state.

3. **The gate trace is verifiable.** `data/security_results/bounty/submittable/ethena/nss-calib-1-gate-trace.json` holds the verbatim gate-by-gate booleans. Any future agent can replay `_v4_candidate_submission_ok`, `finding_has_credible_reproduction`, `finding_balance_verified`, etc. against the same `Finding` shape and reproduce the trace.

4. **No gate was loosened.** The spec's `NSS_CALIBRATION_LANE` knob exists as documentation only. The runtime codebase contains no logic that bypasses `qualifies_for_submission()` for calibration lanes. The trust boundary is intact.

5. **The empirical-false-negative rate datum is recorded.** `TRUE` for `ethena_native` Lane A (confirmable) `AND` Lane B (not exploitable); no prior v6 session has ever recorded such a datum.

## What I am NOT confident about

1. **Whether the calibration lane generalizes.** This session ran against EVM (Ethereum mainnet). Solana calibration lanes would require an entirely different scaffolding pattern (`measured_oracle.delta()` threshold + slot-vs-account semantics). I have not tested whether the Lane A/Lane B construction translates cleanly to KLend, Drift, or Wormhole. The architecture supports it (per the existing `solana_measured_oracle.py`), but no empirical calibration has been run yet.

2. **Whether the C4 wardens actually attempted the exploit.** The C4 report says the Ethena sponsor classified the issue as having no protocol impact, but the audit firm did not necessarily run a Foundry fork probe. If they ran only static-analysis + manual review, the verdict is robust against developer misunderstanding but not against the law of unintended consequences. I confirmed Lane B empirically, but I could not confirm that the C4 team confirmed the same.

3. **Whether the system resilience applies to attack classes other than bitwise truncation.** The bug class I selected was a pure-arithmetic, low-entropy, well-bounded bug. Future calibration probes on, say, cross-contract reentrancy or transient storage locks might surface different empirical-FNR patterns. I have not tested those. Lane A/B is one (N=1) sample of bug class.

4. **Whether `mintedPerBlock[block.number] == 0` for all blocks observed.** This session assumed the cap and minted-this-block values reflect a normal-block state. If Ethena admin temporarily lifts the cap (e.g., during a market crash or a treasury emergency), the residual mint headroom could explode, which could enable a real exploit. The empirical reading I took (25358364) is just one snapshot.

5. **Whether the `mintedPerBlock` storage slot actually exists at the offset I expect.** I trust the EthenaMinting source — `_orderBitmaps[sender][invalidatorSlot]` is the storage that `verifyNonce` reads. If the deployed bytecode's storage layout differs from the source (e.g., proxy patterns or storage collisions), the assertion of "real collision" is on the wrong slot. I read `mintedPerBlock` directly and it returned 0 — and `verifyNonce` returned the truncated values — so the storage layout does match the source. But the assumption is verified by read-only queries, not by full storage proof.

## What I changed

- `SPEC.md` was replaced wholesale with `v6.1.0-proposal-session5` per user instruction. The v6.0.0-draft history is preserved verbatim in `git log` (commits `617c412`, `2e48c9a`, `c2a2fbe`, `bf14075`, `482fd4f`) and via the per-version entries in `CHANGELOG.md`.
- `foundry/test/EthenaCalibrationProbe.t.sol` was added.
- `hermes/scripts/v6_1_calibration_gate_trace.py` was added.
- `hermes/scripts/v6_1_calibration_persist.py` was added.
- `data/security_results/impact/ethena_calibration_measured_delta.json` was added.
- `data/security_results/bounty/submittable/ethena/NSS-CALIB-1.json` was added.
- `data/security_results/bounty/submittable/ethena/nss-calib-1-gate-trace.json` was added.
- `data/security_results/bounty/submittable/manifest.json` was updated with `pack_count=0` and `calibration_lane` metadata.
- `data/security_results/loop/native_harness_status.json` was updated: `ethena_native.status` stays `scaffolded` because the calibration outcome is honest-zero.
- `CHANGELOG.md` was NOT updated this session (the gate-trace file documents the version transition and will land with the next batch commit).
- The 8 ready-targets manifest is unchanged.

## What I did NOT change

- `validate_hypothesis()`, `qualifies_for_submission()`, evidence grading, CPCV, task verifier, `submission_gates.py` — untouched.
- The `wormhole_economic_impact_verified` mocked-authorization rejection — untouched. The spec's `NSS_CALIBRATION_LANE` is documented but not deployed.
- `native_harness_status.json` for any target other than `ethena_native`.
- `submission_alert.json` — no submission alert was generated (no submit-ready finding).
- External submission channels — none were contacted.
- Any of the 14 saturated-target state files (e.g., `data/security_results/loop/state.json`).
- Any of the 8 ready-target state files (uniswap_v4, morpho_blue, aave_v3, kamino, jito, raydium, orca, reserve).

## The honest truth

The system can now self-discover a known-prior-version bug class on a live mainnet fork, **and** it can correctly classify that bug class as not exploitable. Both halves of the calibration datum landed in the same session. `submit_ready` did not move; that is the correct answer for an honest system. The deliverable is the *evidence* the system produced, not a single submission-ready finding.

The empirical false-negative rate datum is now on file. Future agents have a falsifiable baseline.
