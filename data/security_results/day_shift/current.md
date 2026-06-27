# Session plan — v6.27 Enzyme Onyx deep-dive

Status: **closed** (2026-06-27) — v6.27/session-30, target closed. Honest-zero.

# Session plan - v6.27 KAST sidecar final: cross-instance swap, honest-zero

Status: **closed** (2026-06-27) - v6.27/session-28 KAST m_ext + ext_swap sidecar final.
Verdict: **Honest-zero across the full executable instruction surface. H5 retracted as false positive.**

## Summary

v6.27 completed the KAST M0 Solana M Extensions sidecar (Immunefi) with a deep Crucible invariant fuzzing campaign. The harness reached **23 actions** across 2 m_ext instances + ext_swap CPI router, with 0 crashes across ~40,000+ total fuzzing executions and 5+ campaign variants. No confirmed production defects found.

| Phase | Result |
|-------|--------|
| H5 recantation | claim_for collateral check definitively proven correct for crank mode. EXT tokens have no ScaledUiAmount multiplier; comparison is mathematically equivalent to `ext_supply * INDEX_SCALE / m_index <= vault_raw`. |
| Cross-instance swap | Added ext_a (no-yield, second m_ext instance at `3joDhmLtHLrSBGfeAe1xQiv3gjikes3x8S4N3o6Ld8zB`) + ext_swap CPI integration. All ext_swap actions (wrap, unwrap, swap, install) verified. |
| Value conservation invariant | `ext_supply * ext_index <= vault_raw * m_index` after sync. 0 genuine violations. Only stale-index false positives from `update_multiplier` before `sync`. |
| Honest-zero campaigns | Scaled-ui: 2,629 exec/82% ok/0 crashes. Crank: 2,308 exec/61% ok/0 crashes. Both 23/23 actions. |
| Python state model | `src/night_shift_security/native/kast_state_model.py` — systematic wrap/sync/claim/unwrap invariant tests. |

## v6.27 result

`submit_ready=0`. The program has sustained 4 professional audit firms (Asymmetric Research, Adevar Labs, OtterSec, Halborn) and the Crucible fuzzer now exhaustively covers all executable instruction paths. No confirmed production defects.

## v6.27 carry-forward

None. Recommend pivoting to a fresh target with less audit saturation.

## v6.27 references

- `data/security_results/investigations/2026-06-27-v6-27-kast-sidecar/setup.md`
- `data/security_results/investigations/2026-06-27-v6-27-kast-sidecar/property_fanin.md`
- `data/security_results/investigations/2026-06-27-v6-27-kast-sidecar/summary.json`
- `data/security_results/investigations/2026-06-27-v6-27-kast-sidecar/runs.jsonl`
- `data/security_results/investigations/2026-06-27-v6-27-kast-sidecar/strategies/`
- `data/security_results/lab_notebook/2026-06-27-v6-27-kast-sidecar.md`
- `src/night_shift_security/native/kast_state_model.py`
- `sources/crucible/fuzz/kast/src/main.rs`

---

# Session plan - v6.26 Lombard Phase 4-5 corridor endgame

Status: **closed** (2026-06-27) - v6.26/session-29, Phase 4-5 complete. All honest-zero.

## Summary

Full adversarial campaign on Enzyme Onyx (Immunefi, EVM, $200k critical max). 44 source files analyzed, 15 custom tests + 512 fuzz runs, 7 NSS pipeline templates mapped, 6 deep adversarial probes. All honest-zero. See `SPEC.md` §0.0 v6.27 and `lab_notebook/2026-06-27-enzyme-onyx-first-look.md` + `lab_notebook/2026-06-27-enzyme-onyx-solodit-auditvault-correlation.md`.

## Result

`submit_ready=0`. Target closed. Next: rotate to fresh EVM target.

## Carry-forward (unchanged from prior session)

**Lombard lane:**
- `secp256k1_recover` syscall: litesvm limitation prevents BasculeGMP CPI; requires upstream litesvm fix or `solana-test-validator` replay path.
- `lombard_token_pool`: CCIP-based, requires NativeHarness — see `src/night_shift_security/native/lombard.py`.
- `ratio_oracle`: consortium-rotation ratio sequences not exercised in harness — needs dedicated test.

**Pre-existing carry-forward:**
- OnRe human-gate decision (NSS-ONRE-1.json)
- WEB-003 review once Origin reviewers available
- 3F Grunt PositionManager scaffold + H1-prime

---

# Session plan - v6.20 3F Grunt full-scope corpus-driven ultrafuzz
