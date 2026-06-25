# Session plan - v6.19 3F Grunt round 3 audit-gap falsifiers

Status: **open** (2026-06-25) - v6.19/session-23 H13-H19 falsifiers shipped.

## Summary

v6.19 continues the 3F Grunt Cantina bounty hunt from v6.18's H9-H12 honest-zero,
deliberately targeting the **audit-acknowledged / risk-accepted** findings extracted
from the ChainSecurity + Cantina reports. 7 new hypothesis surfaces (H13-H19) chosen
by severity / acknowledgement posture. 46 falsifiers across 7 Foundry harness files,
all green on pinned commit `89cbfa01e5d14c34354ef715757bc84289cc2d04`.

| Phase | Result |
|-------|--------|
| Source pin | Unchanged from v6.16: `sources/3f-grunt/repo` at `89cbfa01e5d14c34354ef715757bc84289cc2d04`. |
| Audit PDFs | Re-read all 4 (ChainSecurity Grunt, ChainSecurity GruntFunds, Cantina Grunt, Cantina Fee Review); extracted acknowledged-risk findings into property fan-in table. |
| Foundry harnesses | 7 new: H13 (10 tests), H14 (7 tests), H15 (6 tests), H16 (5 tests), H17 (6 tests), H18 (6 tests), H19 (6 tests). All 46 green. |
| Regression coverage | manager 231, borrow 180, funds 426, request 406, full project 1795 (+1 skipped). No regressions. |
| NSS validator | 7 new v6.19 presence checks; full NSS suite 878 passed (+12 skipped, +7 from v6.18). |
| H13 falsifiers | 8/8 green: docs Cantina 3.3.21 with concrete magnitude (donation 500e18 → feeRecipient shares ~92.59e18). |
| H14 falsifiers | 7/7 green: flash loan executor scope correctly routes, non-whitelisted scripts revert. |
| H15 falsifiers | 5/5 green: deadline auto-flip PT drain reproduced per Cantina H (accepted). |
| H16 falsifiers | 5/5 green: claim() per-token DoS handled; per-token fail doesn't break other entries. |
| H17 falsifiers | 6/6 green: intervening Morpho activity shifts computed (seized, repaid) math; expected balance gating absorbs. |
| H18 falsifiers | 6/6 green: callback can invoke syncRepaidStatus pre/post-deadline; pullFunds gate is the protection. |
| H19 falsifiers | 6/6 green: ParetoFund epoch gating surfaces (3.3.22, 3.3.23, 3.4.7) all correctly enforced. |
| Tests | 46 new Foundry tests pass; 1795 regression tests pass; NSS suite 878 pass. |

## Hypothesis ledger (priority for v6.20+)

1. **H20+** Property-based Stateful fuzz over H4+H9+H11+H17 surfaces using forge-std's orchestrator — quantitative invariant dom-frame.
2. **H20+** Production-bootstrap PositionManager scaffold (multi-position seeded with debt/collat history) for **H1 production exploitation path that bypasses accepted operational mitigations**.
3. **H8-prime** non-role liquidator nested-callback harness — only worth pursuing if a new signal emerges from property-based fuzz.
4. **H6-prime** Guardian signature bypass with measurable economic loss exceeding the SC-wallet replay mitigation documentation (currently out-of-scope per audit posture).
5. **H7-prime** proxy / beacon storage collision or unprivileged role escalation — admin/beacon-owner gated; killed unless concrete unprivileged reinitialize path surfaces.

## Carry-forward for v6.20+

- Build Stateful-fuzz campaign on the H4/H9/H11 surface using forge-std's orchestrator.
- Production-bootstrap scaffold for PositionManager + multi-borrow-module history.
- Non-role liquidator nested-callback harness for H8-prime.

## Blocks

- [x] H13 finding observed and quantified (Cantina 3.3.21 acknowledged; does not escape gate).
- [x] H14-H19 falsified (honest-zero, audit posture reproduced).
- [x] Re-emitted static probe with invariants intact.
- [ ] H1 production-bootstrap scaffold for v6.20+.
- [ ] First concrete Grunt candidate through `qualifies_for_submission()` (still 0).

## Night Shift handoff

- 46 v6.19 falsifiers pass: leaning on documented protections acknowledged in Cantina
  reports for H14-H19; H13 records the perf-fee-skim magnitude as a quantitative
  datum but does not escape the audit-acknowledged gate.
- The H13 quantitative datum (donation 500e18 → fee shares ~92.59e18) is on disk
  in `sources/3f-grunt/repo/test/manager/GruntH13ExternalDebtFeeInflation.t.sol`.
  Treat this as a falsifier-pass datum measured inside the model, not an
  absence-of-bug proof.
- v6.15 WEB-003 and v6.13 NSS-ONRE-1 remain `submit_ready=1`; this session must
  not autonomously submit or publish them.
- Re-run `hermes/scripts/v6_16_grunt_static_probe.py` whenever the Grunt
  pinned commit or in-scope file surface changes; diff the `invariants` map
  against the baseline envelope.
- Solodit / Cantina corpus sync continue at `hermes/scripts/nss-hipif-chain.sh`.

## References

- `SPEC.md` v6.18.0-grunt-round2-session22
- `CHANGELOG.md` v6.19 — audit-gap falsifiers
- `data/security_results/lab_notebook/2026-06-25-session-23-3f-grunt-v619-round3.md`
- `data/security_results/investigations/2026-06-25-v6-19-3f-grunt-round3/README.md`
- `data/security_results/investigations/2026-06-25-v6-16-3f-grunt-static-probe/grunt_static_probe.json`
- `sources/3f-grunt/repo/test/manager/GruntH13ExternalDebtFeeInflation.t.sol`
- `sources/3f-grunt/repo/test/request/GruntH14FlashLoanExecutorScope.t.sol`
- `sources/3f-grunt/repo/test/request/GruntH15DeadlineAutoFlipDrain.t.sol`
- `sources/3f-grunt/repo/test/facility/GruntH16ClaimBlockedTokenDoS.t.sol`
- `sources/3f-grunt/repo/test/borrow/GruntH17PreLiquidateMEV.t.sol`
- `sources/3f-grunt/repo/test/request/GruntH18OnRequestConsumedReentrancy.t.sol`
- `sources/3f-grunt/repo/test/funds/pareto/GruntH19ParetoEpochGating.t.sol`
- `tests/test_native_grunt.py`
- ~/.factory/specs/2026-06-24-v6-19-audit-gap-falsification-round-3.md

---

## v6.18 archive (session-22)

v6.18 continued the 3F Grunt Cantina bounty hunt from v6.17's H4 honest-zero,
targeting 4 new unexplored hypothesis surfaces: H9 (preLiquidate math rounding),
H10 (CentrifugeFund attacker deposit pollution), H11 (burn multi-position with
skipLtvCheck and interest), and H12 (performance fee avoidance via bad-debt
bootstrap sentinel). 23 falsifiers across 4 Foundry harness files, all green
on pinned commit.

(See prior session archive below for full detail.)

## Carry-forward for v6.19

- Audit re-read: extract acknowledged-risk findings into property fan-in.
- New falsifier frame: weaponise audit-acknowledged gaps; document what holds.

## Blocks (closed)

- [x] H9/H10/H11/H12 falsifiers (23 tests) shipped.
- [x] Static probe re-emitted (9 invariants intact).
- [ ] H1 production-bootstrap scaffold for v6.20+.
- [ ] First concrete Grunt candidate through `qualifies_for_submission()` (still 0).
