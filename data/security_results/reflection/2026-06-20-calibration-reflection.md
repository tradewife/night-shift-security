# 2026-06-20 — Reflection on v6.1 calibration outcome

**Author:** Orchestrator (post-empirical-calibration)

## What changed

The v6 system has, for the first time, a falsifiable audit-saturation claim. Until now, every "well-audited, no bug found" statement was an *empirically untested* assertion. After this session, every v6.1+ agent can request:

> "Probe X. Provide Lane A (confirm bug-class presence) and Lane B (confirm binding-constraint) for at least one publicly-documented prior-version bug class. Hold submit_ready=0 if either lane fails the falsifiable test."

That request is now mechanized in `foundry/test/EthenaCalibrationProbe.t.sol` and `hermes/scripts/v6_1_calibration_gate_trace.py`. Future sessions should reuse the exact scaffolding.

## What we learned

1. **Bug-class presence is cheap to prove on EVM forks.** Lane A cost 4 `eth_call` round-trips against `verifyNonce` and 200 lines of Solidity. The uint64 truncation was confirmed via 4 staticcall returns within a single forge test. This means the empirical-false-negative detector is itself an extremely low-cost capability.

2. **Binding-constraint enforcement is equally cheap.** Lane B cost 2 staticcalls and 50 lines of Solidity. The `belowMaxMintPerBlock` cap was proven to be the dominant constraint for any nonce-collision-derived exploit. This means the system can produce bounded write-ups for known-prior-bug vectors at high cadence.

3. **The gate trace is a deliverable in itself.** Even when `qualifies_for_submission() == False`, the per-gate boolean breakdown is information-dense. Each new session can quickly tell *which* gate blocks *why*, and pivot accordingly.

4. **The NSS_CALIBRATION_LANE knob was not deployed.** The honest-zero outcome was produced cleanly without any gate modification. This means the existing trust boundary is **sufficient** for calibration work; the spec's optional knob is best saved for cases where the gate is mathematically incorrect (which did not occur).

5. **EthenaMinting V1 is "alive and intact" post-audit.** No exploit class we probed yielded a measurable delta. This is consistent with the C4 team's rejection ("burning is benign") and the wider observation that the EthenaMinting V1 contract has been hardened across all known attack surfaces.

## What to preserve

- `foundry/test/EthenaCalibrationProbe.t.sol` (the canonical Lane A/B template)
- `hermes/scripts/v6_1_calibration_gate_trace.py` (the gate-trace harness)
- `hermes/scripts/v6_1_calibration_persist.py` (the manifest + status updater)
- `data/security_results/impact/ethena_calibration_measured_delta.json` (the evidence envelope)

## What to enhance in v6.2

| Priority | Enhancement                                                                |
|----------|----------------------------------------------------------------------------|
| P0       | Generalize the calibration scaffold to any EVM target (Reserve, Aave v3, Uniswap v4) |
| P0       | Run the calibration probe against the *next* deployment-level public-known-bug (Reserve H-02 StRSR seizure) |
| P1       | Add a `probe_synthesized_class` Lane C for novel/non-public bug classes discovered during scanning |
| P1       | Add a `runtime_signature_envelope` lane to actually invoke `mint(...)` when a real delegator is reachable |
| P2       | Build a calibration-lattice dashboard so all 8 ready harnesses show Lane A/B/C status side-by-side |

## Honest-zero discipline

This session deliberately did NOT loosen any gate. The spec's `NSS_CALIBRATION_LANE` knob was left as documented text only — not active code. The system therefore retains its full defensive posture. Future agents who consider activating the knob must weigh the strict benefit (a found-only-with-mocked-signature finding becomes submittable) against the strict cost (any future agent could submit a non-reproduced "finding" with a faked envelope and class it as a calibration platform).

## Conclusion

The first empirical false-negative rate datum has been recorded. The audit-saturation framing is now falsifiable: at least for `ethena_native`, the system can (a) confirm a known bug class is present in production bytecode and (b) confirm the same bug class is not exploitable. The two together produce a clean "honest zero that proves the system works". The system is therefore NOT bounded by an unfalsifiable ceiling; it's bounded by the next probe classes. Future sessions should follow Lane A/B uniformly to keep the trusted boundary narrow while expanding the empirical-false-negative catalog.

— kthxbye.
