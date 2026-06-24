# Session plan - v6.16 3F Grunt substrate

Status: **open** (2026-06-24) - v6.16/session-20 substrate bootstrapped.

## Summary

v6.16 pivoted from the Origin web attack surface back to a fresh EVM target:
the 3F Grunt Cantina bounty (live since 2026-06-02, $250K Critical). The
session prioritized source pinning, scope-aware inventory, and a bounded
hypothesis ledger under the strict Cantina out-of-scope policy. Executable
attempts (Foundry + multicomponent EVM setup) were intentionally deferred so
the substrate is captured cleanly.

| Phase | Result |
|-------|--------|
| Source pin | Fetched `3FLabs/grunt` shallow 50 commits to `sources/3f-grunt/repo`; pinned at `89cbfa01e5d14c34354ef715757bc84289cc2d04`. |
| In-scope inventory | 103 Solidity files; 102 in-scope, 1 out-of-scope (`src/facility/IntentDescriptor.sol`). |
| Audit PDFs | Recorded four in-repo PDFs from chainsecurity and Cantina audits (April-May 2026). Audit baseline commit `7056bb17257b7745fed054e7ba158f5f48cfda2c` (ChainSecurity Grunt) referenced. |
| NativeHarness | Added `src/night_shift_security/native/grunt.py`: 12 selector tables, role maps, EIP-712 typehashes, PM constants, scope_notes. |
| Static probe | `hermes/scripts/v6_16_grunt_static_probe.py` re-checks 9 canonical invariants on the pinned commit; all 9 confirmed present. JSON envelope at `data/security_results/investigations/2026-06-24-v6-16-3f-grunt-static-probe/grunt_static_probe.json`. |
| Hypothesis ledger | 8 entries (H1/H3/H4/H5/H6/H7/H8-prime variants) with bounty out-of-scope kill-criteria. |
| Tests | `tests/test_native_grunt.py`: 9 passed; full suite 866 passed, 12 skipped. |

## Hypothesis ledger (priority for next session)

1. **H1-prime** share-inflation via external Morpho donation *that bypasses accepted operational mitigations and the production-bootstrap path*.
2. **H3-prime** Request pull / repay / authorizeMinting path *exceeding accepted Facilitator/Consumer trust* (independent violation of min/max balance or mint-to-repaid delay).
3. **H4-prime** rounding / proportional-distribution edge cases *leaving LTV > safe LTV* post-operation, without already-detectable bad-debt precondition.
4. **H5-prime** async fund state-machine impact reachable by non-operator users *outside* accepted settlement delays.
5. **H7-prime** proxy / beacon storage collision or unprivileged role escalation *not* dependent on admin mistakes.
6. **H8-prime** reentrancy / callback abuse via `onMorphoRepay` / `preLiquidate` outside the documented "liquidator is not a Facilitator/MINTER" assumption.
7. H6-prime is documented as out-of-scope unless it bypasses guarded assumptions.

## Carry-forward for v6.17+

- Build targeted Foundry tests for H1-prime, H3-prime, H4-prime against a
  seeded PositionManager + Morpho mock.
- Use the Cantina baseline commit (`7056bb17257`) as a comparison anchor
  once a deeper fetch of the upstream history is performed.
- Confirm whether the audited EIP-712 SC-wallet replay mitigation actually
  shipped to main (signature binding). If still absent on main, that finding
  must still be paired with a measurable economic impact to gain
  submission-gated status under the current bounty policy.
- Re-run static probe on every commit that touches the in-scope files and
  diff the `invariants` map against the baseline envelope.

## Blocks

- [x] 3F Grunt source pinned at `89cbfa01e5d14c34354ef715757bc84289cc2d04`.
- [x] NativeHarness + tests + static probe shipped.
- [x] Hypothesis ledger with kill-criteria per item.
- [ ] Foundry tests for at least one H1/H3/H4-prime candidate.
- [ ] First concrete Grunt candidate through `qualifies_for_submission()`.

## Night Shift handoff

- Do not promote any 3F Grunt candidate unless it bypasses the explicit
  bounty out-of-scope categories recorded in `sCOPE_NOTES`.
- Maintain the static probe invariant map; the next operator should copy the
  existing envelope as `grunt_static_probe.json.bak` before each run.
- OnRe `NSS-ONRE-1` and Origin `WEB-003` remain the active
  `submit_ready=1` packs; this session must not autonomously submit or
  publish them.
- Solana-first per SPEC §4.4 remains true overall; v6.16 is the EVM
  parallel track that benefits Cantina-target v6 onboarding.

## References

- `SPEC.md` v6.16.0-grunt-session20
- `CHANGELOG.md` v6.16 — 3F Grunt deep-dive substrate
- `data/security_results/lab_notebook/2026-06-24-session-20-3f-grunt-substrate.md`
- `data/security_results/investigations/2026-06-24-v6-16-3f-grunt-static-probe/grunt_static_probe.json`
- `sources/3f-grunt/source_manifest.json`
- `src/night_shift_security/native/grunt.py`
- `tests/test_native_grunt.py`
- `hermes/scripts/v6_16_grunt_static_probe.py`
