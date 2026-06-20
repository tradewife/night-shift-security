# 2026-06-20 — Reflection on v6.2 Marginfi onboarding outcome

**Author:** Orchestrator (post-McNativeHarness-onboard session)

## What changed

The Marginfi v2 substrate is now a first-class member of the v6 harness family. Every future session that wants to probe a Solana lending sibling to Kamino can reuse `src/night_shift_security/native/marginfi.py` with the same Python mocking and Solana RPC patterns that already work for Kamino. The "sibling-substrate" generalization v6.1 hinted at has its second datapoint.

The v6.1 calibration pivot produced a single empirical-FNR datum against Ethena. v6.2 produces a *discovery-gap datum* against Marginfi — same lane of evidence (the system can honestly record the absence of a measured finding) but on a different substrate. The dataset's "honest-zero coverage" is now wider than "audit-saturation framing is unfalsifiable", because both datapoints were produced with identical harness-and-gate discipline.

## What we learned

1. **Harness template reuse really works.** The kamino.py shape (program IDs + top-10 instruction discriminators + IDL loader + AccountResolution + resolve_market/resolve_accounts) was copy-pasted into marginfi.py with full test parity within one session. This is the natural consequence of the "sibling substrate" intuition baked into v5 NativeHarness substrate (`src/night_shift_security/native/__init__.py`).
2. **Anchor sighash discriminators are not stable across Anchor SDK versions.** I confirmed via `anchor_discriminator("lending_account_borrow")` returning `0x047e74353005d41f` — but the live Anchor IDL serialized by `anchor build` may use the older `global:` prefix convention. The v6.2 session tests pin the canonical helper-derived discriminator. If the deployment has the program built under a different Hash format, on-chain parsing would mismatch.
3. **The "pending_discovery" sentinel is a load-bearing fail-fast contract.** By hard-coding `DEFAULT_MARGINFI_GROUP = "PENDING_MARGINFI_GROUP_DISCOVERY"` and friends, the probe driver cannot accidentally produce `measured_impact=True` against fake addresses. The sentinel is the one-line equivalent of the `wormhole_economic.harness_auth_mocked=False` rejection.
4. **Theasurement discipline scales across substrates.** The same gate-trace + finding-envelope pair works for both EVM (Ethena) and Solana (Marginfi) without any cross-substrate adaptation. The `_v4_candidate_submission_ok` blocker surfaces cleanly in both lanes (the impact_oracle.measured=False field is substrate-agnostic).
5. **Documentation noise was bigger than probe complexity.** The session spent more cycles hunting for canonical Marginfi v2 group PDA seeds than running the actual probe. The next session should prototype a `getProgramAccounts` filter with `dataSize` matching the on-chain Bank struct layout (~1300 bytes after discriminator prepended to Marginfi Bank struct).

## What to preserve

- `src/night_shift_security/native/marginfi.py` — the sibling-NativeHarness template
- `tests/test_native_marginfi.py` — the test parity surface
- `hermes/scripts/v6_2_marginfi_probe.py` — the read-only probe driver
- The sentinel-default contract (`DEFAULT_* = PENDING_*_DISCOVERY`) — load-bearing
- The honest-zero evidence envelope + gate trace JSON pair

## What to enhance in v6.3

| Priority | Enhancement |
|----------|-------------|
| **P0** | Resolve canonical Marginfi v2 group + USDC bank PDA seeds; persist to `sources/marginfi/marginfi_accounts.json`; re-run probe; flip from `scaffolded` → `ready` |
| **P0** | Implement the v6.1 §10.2 Storage H-02 StRSR era-reset probe as the **3rd empirical-FNR datapoint** (now covering EVM fork hardening substrate) |
| **P1** | Add a focused borrow-coverage test (`MarginfiBorrowStaleOracle.test.ts`) that issues an actual flashloan + borrow with stale Pyth prices to assert `MAX_PRICE_AGE_SEC` enforcement |
| **P1** | Add a `forge`/Anchor test scaffold to the harness so `impact_oracle.measured=True` becomes reachable on Solana (right now Solana substrate depends entirely on `live_executed` cross-slot observation) |
| **P2** | Build a calibration-lattice dashboard so all 10 harness rows show Lane A/B/C status side-by-side |

## Honest-zero discipline

The probe refused to coerce `measured_impact=True` despite the system having RPC access to Marginfi v2 program. The honest-zero outcome is documented in three artifacts:
- `data/security_results/impact/marginfi_v2_measured_delta.json` — evidence envelope with `sentinel_defaults_unresolved` classification
- `data/security_results/bounty/submittable/marginfi_v2/NSS-MFI2-1.json` — finding-shape envelope with `submit_ready=False`
- `data/security_results/bounty/submittable/marginfi_v2/nss-mfi2-1-gate-trace.json` — per-gate booleans

The next session that wants to bypass this requires populating canonical addresses. There is no synthetic-data backdoor.

## Conclusion

Two empirical datapoints recorded (Ethena + Marginfi) across two substrates (EVM + Solana). Both honest-zero. The system's audit-saturation framing is now bounded, not asserted. The next session's most-probable advance is **populating canonical Marginfi addresses** OR **running Reserve H-02 StRSR as the third datapoint**, with neither requiring a gate loosening.

— kthxbye.
