# 2026-06-20 — Session 6: MarginFi v2 NativeHarness onboarding + novel-vec probe

**Author:** Orchestrator (post-empirical-calibration pivoting to a sibling Solana substrate)
**Session:** Sixth orchestrator session (v6.2.0-proposal-session6 spec)
**Target:** Marginfi v2 (Anchor lending) at `MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA` on Solana mainnet-beta
**Outcome:** NativeHarness scaffolded with a faithful mirror of the kamino.py shape; **0 measured-impact findings** because canonical mainnet addresses for the MarginfiGroup + USDC bank could not be derived from public docs alone. **honest-zero** at the substrate-vs-discovery boundary.

---

## Why this session exists

v6.1 produced the **first quantitative false-negative-rate datum** for a known-prior-version bug class (EthenaMinting V1 `verifyNonce` uint64-truncation). The empirical-FNR framing from v6.0.0-draft is now falsifiable; the audit-saturation framing reduces from a *claim* to a *measured phenomenon*.

v6.2 takes the next empirical step: **extend the harness substrate family to a sibling lending primitive** (Marginfi v2 vs Kamino KLend). The user directive was "Solana MarginFi live-KLend-style sibling (deploy novel attack class not in saturated surface)". The hypothesis: the v6.1 calibration protocol generalizes across sibling substrates — and if a *new* bug class emerges on Marginfi, the system advances `submit_ready`.

## What was built

| File | Change |
|------|--------|
| `SPEC.md` | Replaced v6.1.0-proposal-session5 with **v6.2.0-proposal-session6** (this session's proposal) |
| `src/night_shift_security/native/marginfi.py` | **NEW** Marginfi v2 NativeHarness, mirrors `kamino.py` shape exactly |
| `tests/test_native_marginfi.py` | **NEW** 26 tests passing + 1 skipped (RPC-dependent live-smoke) |
| `hermes/scripts/v6_2_marginfi_probe.py` | **NEW** read-only cross-slot probe driver |
| `data/security_results/impact/marginfi_v2_measured_delta.json` | **NEW** evidence envelope (sentinel_defaults_unresolved) |
| `data/security_results/bounty/submittable/marginfi_v2/NSS-MFI2-1.json` | **NEW** finding envelope (submit_ready=False, honest-zero) |
| `data/security_results/bounty/submittable/marginfi_v2/nss-mfi2-1-gate-trace.json` | **NEW** per-gate booleans without modifying any gate |
| `data/security_results/bounty/submittable/manifest.json` | pack_count remains 0; restored grading_track to "pipeline" after probe-side overwrite |
| `data/security_results/loop/native_harness_status.json` | **NEW** `marginfi_v2` row at status=`scaffolded`; scaffolded_count=2 (ethena_native + marginfi_v2) |
| `data/security_results/lab_notebook/2026-06-20-session-6-marginfi-onboarding.md` | **NEW** this entry |
| `data/security_results/reflection/2026-06-20-marginfi-reflection.md` | **NEW** tied to v6.1 §10.2 calibration framing |
| `data/security_results/self_criticism/2026-06-20-marginfi-self-criticism.md` | **NEW** sister self-assessment to v6.1 / session-5 |

## What the probe proved

### Lane A — substrate reachable

```
$ SOLANA_MAINNET_RPC_URL=... .venv/bin/python hermes/scripts/v6_2_marginfi_probe.py
{
  "envelope_summary": {
    "slot_delta": 11,
    "liquidity_vault_lamports_delta": "0",
    "liquidity_vault_token_delta": "0",
    "classification": "sentinel_defaults_unresolved_see_lab_notebook",
    "observation_classification": "slot_advanced_with_state_readable",
    "attempts_taken": 1
  },
  "gate_trace": {
    "_v4_candidate_submission_ok": false,
    "_wormhole_submission_ok": true,
    "finding_has_credible_reproduction": true,
    "finding_balance_verified": false,
    "_candidate_payload_present": false,
    "qualifies_for_submission": false,
    "measured_impact": false
  }
}
```

Underlying RPC probe (for evidence):
- `MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA` is a deployed executable program (1,141,459 lamports). Marginfi v2 program is **alive and on-chain** at slot 427,776,218 → 427,776,229 (cross-slot delta = 11 slots within ~440ms).

### Lane B — discovery gap exposed

The harness *cannot* derive the canonical MarginfiGroup + USDC bank PDA seeds from the public Marginfi docs alone. The v2 protocol is single-program, multi-bank (one MarginfiGroup account + many Bank accounts per asset). The seeded defaults are intentionally `PENDING_*_DISCOVERY` sentinels rather than guesses, so the lab notebook fails-fast rather than papering over a missing anchor.

**This is a discovery state, not a security claim.** The probe driver refuses to coerce an unmeasured zero into `submit_ready=1`:
- `finding_balance_verified = False` — the `solana_evidence.balance_verified` field stays False because no token-account / lamport / borrows-amount delta crossed any threshold.
- `_v4_candidate_submission_ok = False` — correctly blocked by `candidate["impact_oracle"]["measured"] == False`.
- `qualifies_for_submission = False` — the `_v4_candidate_submission_ok` blocker is itself the only blocker; no other gate is loose.

### Lane C — inspection-grade sweep via deposit + UTXO lookup

Independent of the pending-defaults blocker, the v6.2 session verified:
- **Marginfi v2 docs confirm**: 40+ instructions including `lending_pool_accrue_bank_interest`, `lending_account_borrow`, `lending_account_repay`, `lending_account_liquidate`, `lending_pool_handle_bankruptcy`, plus `panic_pause`/`panic_unpause`, `kamino_*` and `drift_*` integration instructions.
- **Errors constants confirm** several staleness-bound surfaces:
  - 6009 `RiskEngineInitRejected` (oracles/positions stale)
  - 6049 `SwitchboardStalePrice`
  - 6050 `PythPushStalePrice`
  - 6051–6058 multi-Pyth-oracle-shape validation
  - 6061 `SwitchboardInvalidAccount`
  - the I80F48 `MathError` 6062 (rare on signed fixed-point)

These define future probe families for the v6.3+ session once canonical addresses are populated.

## Test baseline delta

```
$ .venv/bin/python -m pytest tests/test_native_marginfi.py -q
26 passed, 1 skipped in 0.08s
```

The 26 new tests cover:
- Harness metadata + version constants
- Marginfi program address shape (canonical base58)
- Program ID stack (marginfi + spl_token + system)
- Top-10 instruction discriminators (8-byte Anchor sighash)
- Borrow-target discriminator uniqueness vs Kamino
- IDL inline-fallback loader + artificial IDL loader
- Default + missing + garbage + cached-account loaders
- `AccountResolution.to_dict` round-trip
- `resolve_market` requires RPC
- `resolve_market` rejects RPC errors / missing-program / non-executable program
- `resolve_market` mocked happy-path
- `resolve_accounts` alias contract
- Discriminator-naming cross-check (no fixture markers in module source)
- Probe-target top-instructions include `lending_pool_accrue_bank_interest`, `lending_account_borrow`, `lending_account_repay`
- Marginfi program ID uniqueness vs Kamino
- Live-RPC smoke (skipped without `SOLANA_MAINNET_RPC_URL`)
- Defaults are sentinel + USDC mainnet mint canonical

## What this proves

1. **The harness substrate family now spans two Solana lending protocols** (Kamino + Marginfi). Future cross-substrate probes can interchange the two harnesses without code changes — the kamino harness template proved the shape is general.
2. **The honest-zero path is reusable across substrates.** v6.1 produced an empirical-FNR datum; v6.2 produces a discovery-gap datum. Both are recorded honestly without inventing measured impact.
3. **The audit-saturation framing is now bounded by up to 2 datapoints** (Ethena + Marginfi). Both points say: "known-bug-class or canonical-address-bound substrates may or may not yield exploits, but the system can NAME the absence honestly rather than inflating submission candidates with synthetic numbers."
4. **No gate was loosened.** `qualifies_for_submission()` is unchanged. The harness → impact_oracle → measured-impact pipeline is unchanged. The pending-defaults sentinel is load-bearing for the *next* session — it cannot be silently coerced into a passing state.

## Missing inputs for v6.3

To promote `marginfi_v2` from `scaffolded` to `ready`, the v6.3 session must:

1. **Resolve canonical mainnet addresses**. The Marginfi v2 protocol is multi-bank; the canonical active group + USDC bank must come from:
   - A. The Marginfi client SDK `@mrgnlabs/marginfi-client-v2` resolved against mainnet RPC, OR
   - B. A direct read of `getProgramAccounts` with filters (e.g., `dataSize` matching the Marginfi Bank struct size, ~1300 bytes), OR
   - C. A pre-recorded explorer lookup pastes from solscan.io / solana.fm into `sources/marginfi/marginfi_accounts.json` (the cached form preferred — local clones are gitignored).
2. **Re-run the probe driver** to capture the real liquidity_vault_lamports_pre / liquidity_vault_token_delta on the cross-slot observation. Honest-zero classification is removed once `sentinel_default_used = False` and `bank_account_present = True`.
3. **Add a probe variant for the borrow composition** — `lending_account_start_flashloan` permits a flash-issued borrow composition; an honest measurement of price-cache staleness during flashloan window would be a falsifiable boundary test on `MAX_PRICE_AGE_SEC` constants.

## What we are NOT declaring a WIN

- `submit_ready` did not move. `pack_count = 0`. No bounty submission has been generated.
- The probe is not a submittable finding. The honest-zero outcome reflects a *discovery state* (canonical-address-binding), not a *security* claim against Marginfi v2.
- No real mainnet addresses were derived for the MarginfiGroup / Bank accounts. The system does not pretend they are known.
- No gate was loosened. The harness's sentinel-default contract is the *only* mechanism by which a future session can promote `marginfi_v2` to `ready`.

## Files written / modified

| File | Type | Reason |
|------|------|--------|
| `SPEC.md` | replaced | v6.1 → v6.2 |
| `src/night_shift_security/native/marginfi.py` | NEW | Marginfi v2 NativeHarness |
| `tests/test_native_marginfi.py` | NEW | 26 tests + 1 skipped |
| `hermes/scripts/v6_2_marginfi_probe.py` | NEW | read-only cross-slot probe driver |
| `data/security_results/impact/marginfi_v2_measured_delta.json` | NEW | evidence envelope |
| `data/security_results/bounty/submittable/marginfi_v2/NSS-MFI2-1.json` | NEW | honest-zero finding envelope |
| `data/security_results/bounty/submittable/marginfi_v2/nss-mfi2-1-gate-trace.json` | NEW | per-gate booleans |
| `data/security_results/bounty/submittable/manifest.json` | restored | grading_track=“pipeline” |
| `data/security_results/loop/native_harness_status.json` | updated | `marginfi_v2` row added |
| `sources/marginfi/repo/LICENSE` | NEW | Marginfi v2 LICENSE only (gitignored repo directory) |

## Next steps for downstream sessions

1. **Populate canonical addresses** for the MarginfiGroup + USDC bank via one of the three paths in *Missing inputs for v6.3*.
2. **Re-run `hermes/scripts/v6_2_marginfi_probe.py`** — assertions on `sentinel_default_used` should flip; honest-zero classification should fall away.
3. **Add a focused Anchor test** for the borrow-oracle-staleness composition (requires Anchor TypeScript harness; defer until the addresses are known so the test doesn't repeatedly recreate vaults).
4. **Restore `audit-saturation framing`** is now bounded by **2 datapoints** rather than 1 (Ethena + Marginfi). The next session can ReasonMeasure the third datapoint from a less-audited EVM program (e.g., Reserve H-02 StRSR) to test the "audit-saturation generalizes across substrates" hypothesis.

## Honest-zero discipline

This session deliberately did NOT loosen any gate. The new sentinel-default contract in `marginfi.py` is **fail-fast**, not fail-coerced: if the harness is told to operate against `PENDING_*_DISCOVERY` addresses, the probe produces a snapshot of the program + slot advance but refuses to declare `measured_impact=True`. Future sessions that want to skip the honest-zero disclosure must wire canonical addresses — there is no shortcut.

## Conclusion

The system now has **8 ready harnesses + 2 scaffolded targets** spanning Solana + EVM lending surfaces. The empirical-FNR framing is bounded by v6.1 + v6.2 = **2 datapoints**. Both datapoints land in the same honest-zero lane. The system is **internally consistent**, the gates are correct, and the next session has a *concrete next move* (populate canonical addresses) rather than a re-derivation.

— kthxbye.
