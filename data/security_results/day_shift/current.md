# Session plan — v6.27 Enzyme Onyx deep-dive

Status: **closed** (2026-06-27) — v6.27/session-30, target closed. Honest-zero.

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
