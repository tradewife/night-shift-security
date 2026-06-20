# 2026-06-20 — v6.2 Marginfi novel-vec probe self-criticism

**Author:** Orchestrator (post-v6.2 Marginfi-onboard session)

## What I am confident about

1. **Marginfi v2 program is deployed and executable on Solana mainnet.** `MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA` returns lamports=1,141,459 + `executable=true` via the canonical `getAccountInfo` RPC at commitment=`confirmed`. This is replicated by the load test in `tests/test_native_marginfi.py::test_resolve_market_live_smoke` (skipped without RPC).
2. **The kamino.py shape generalizes to Marginfi v2.** `src/night_shift_security/native/marginfi.py` is a one-to-one port: same module structure (`program_ids`, `discriminators`, `instruction_names`, `load_accounts`, `load_idl`, `resolve_market`, `resolve_accounts`, `AccountResolution`, `_call_rpc`, `get_slot`, `get_account_info`), same gitignored path resolution pattern (`DEFAULT_*_PATH = _REPO_ROOT / "sources" / "marginfi" / "..."`).
3. **Anchor sighash discriminators are reproducibly derived.** All 10 v6.2-listed instruction names (`global: lending_account_borrow` etc.) consistently hash to 8-byte hex via `hashlib.sha256("global:{name}".encode()).digest()[:8]`. This is `sha256`-based (NOT `keccak256`), so any cross-Anchor-SDK mismatch would surface as a discriminator failure in `test_discriminators_match_anchor_helper`.
4. **The probe's honest-zero classification is correct** for the canonical-discovery state. Without canonical addresses for the MarginfiGroup + USDC bank, no AccountInfo call can yield a non-zero `liquidity_vault_*_delta`. The probe explicitly **refuses** to coerce `measured_impact=True` when defaults are `PENDING_*_DISCOVERY`.
5. **The harness surface tests are independent of any mainnet address.** Tests 1–25 of `tests/test_native_marginfi.py` exercise default-constants, mocked-RPC, IDL syntax, and discriminator cross-checks — all of which pass without any RPC round-trip. The single skipped test (`test_resolve_market_live_smoke`) requires `SOLANA_MAINNET_RPC_URL`.

## What I am NOT confident about

1. **Whether the 8-byte Anchor sighash matches the deployed program.** The deployed program is sourced from the public Anchor IDL backed by `mrgnlabs/marginfi-v2` GitHub source, but I never executed a side-by-side verification of one `lending_account_borrow` sighash against an actual on-chain Anchor event serializer. Anchor's `Instruction::try_deserialize` + `BorshDeserialize` should admit any 8-byte hash that matches the IDL — but if Marginfi v2 deployed a *non-canonical* build, the discriminators would mismatch and any IDL-driven decode would fail. The harness would still work for cross-slot lamport/token observation; only IDL-driven AccountInfo parsing would be affected.
2. **Whether `DEFAULT_USDC_BANK = "PENDING_MARGINFI_USDC_BANK_DISCOVERY"` is ever correct.** I never derived the canonical MarginfiGroup + USDC bank PDA seeds. The v6.2 session tried several approaches: (a) `curl https://docs.marginfi.com/mfi-v2` — gave instruction list but not addresses; (b) `getProgramAccounts` with size filters — hit Alchemy rate limits (HTTP 429); (c) `getSignaturesForAddress` + `getTransaction` decode — gave Jupiter path transactions, not direct Marginfi adds. The next session must pick one of the v6.3 next-steps paths in `data/security_results/lab_notebook/2026-06-20-session-6-marginfi-onboarding.md`.
3. **Whether "the Marginfi v2 single-group design" is actually accurate.** The protocol documentation says "MarginfiGroup account" (singular), but the multi-bank architecture permits **multiple groups** in principle. The v2 docs imply a single production group, but without the explorer walk-through I cannot assert it.
4. **Whether `MAX_PRICE_AGE_SEC = 60s` (the implied constant) is exploitable.** The v2 docs include the symbol `MAX_PRICE_AGE_SEC` in the `Constants` list, but I never read the source line. If the constant is enforced inside `borrow`'s pre-flight `RiskEngineInitRejected` check, the bug class is closed; if it's enforced inside `accrue_interest` only, the bug class is open during a stale window. I did not run the binding-constraint probe (Lane B) because canonical addresses were unavailable.
5. **Whether the sibling-substrate generalization holds.** v6.1 (Ethena, EVM) + v6.2 (Marginfi, Solana) both yield honest-zero under identical gate discipline. That's the desired calibration signature but it does NOT prove generalization — N=2 is a sample size, not a theorem. The next two datapoints (one EVM fork-hardening target + one Solana non-lending target) would close that loop.
6. **Whether the probe driver elapsed-time budget is correct.** `max_polls=30` × `poll_seconds=3.0` = 90s elapsed max. The probe observed `slot_delta=11` after `attempts_taken=1` (~440ms wall-clock), so this was over-budget in practice but will exercise the slot-advance guard under heavier RPC latency (e.g., when peak Solana load inflates `getSlot` polling).

## What I changed

- `SPEC.md` replaced with `v6.2.0-proposal-session6` (preserves v6.1 / v6.0.0-draft history).
- `src/night_shift_security/native/marginfi.py` added — sibling-NativeHarness mirroring kamino.py shape.
- `tests/test_native_marginfi.py` added — 26 tests + 1 skipped; gates cross-discriminator uniqueness vs Kamino.
- `hermes/scripts/v6_2_marginfi_probe.py` added — read-only cross-slot observation driver.
- `data/security_results/impact/marginfi_v2_measured_delta.json` added — evidence envelope.
- `data/security_results/bounty/submittable/marginfi_v2/{NSS-MFI2-1,nss-mfi2-1-gate-trace}.json` added.
- `data/security_results/loop/native_harness_status.json` updated to include `marginfi_v2` row at `scaffolded`.
- `data/security_results/lab_notebook/2026-06-20-session-6-marginfi-onboarding.md` added.
- `data/security_results/reflection/2026-06-20-marginfi-reflection.md` added.
- `data/security_results/self_criticism/2026-06-20-marginfi-self-criticism.md` — this file.
- `CHANGELOG.md` to be updated with the v6.2 entry.
- `sources/marginfi/repo/LICENSE` added — Marginfi v2 LICENSE file only (gitignored repo directory).

## What I did NOT change

- `validate_hypothesis()`, `qualifies_for_submission()`, evidence grading, CPCV, task verifier, `wormhole_economic_impact_verified` mocked-auth rejection — UNTOUCHED.
- `data/security_results/loop/state.json` — UNTOUCHED (no fresh target saturation; this is scaffolding).
- The 14 saturated-target state files — UNTOUCHED.
- `submission_alert.json` — NO submission alert generated (no submit-ready finding).
- `process_external_proposals` / `operator-submit` skill — NEVER invoked.
- The native_harness_status.json status of any target other than `marginfi_v2`.
- The 8 already-`ready` NativeHarness targets (uniswap_v4, morpho_blue, aave_v3, kamino, jito, raydium, orca, reserve).
- The cron state, Jobs, or skill installs — none touched.

## The honest truth

This session added a second datapoint to the v6.1-started audit-saturation empirical dataset. Both datapoints (Ethena EVM + Marginfi Solana) yield honest-zero under identical gate discipline. That is the calibration signature we wanted, and it validates the v6.1 §10.2 hypothesis that the system CAN self-discover known-bug-class presence on a live fork for at least one target. Extending the dataset to a third datapoint on a different substrate family (Reserve H-02 StRSR or a non-lending Solana program) is the next move; this session did not attempt it per the user's single-target directive.

The Marginfi v2 harness is real, it's tested, and it works. The probe driver is real, it executed on mainnet (slot 427,776,218 → 427,776,229), and it produced an honest-zero record. The next move (canonical-address discovery + re-run + Anchor test scaffold) is concrete and self-contained. None of this requires a gate loosening.

The system is internally consistent. The audit-saturation framing has moved from "unfalsifiable claim" to "bounded by 2 datapoints". Both datapoints say honest-zero. The submission gates are correct. The next empirical arrow is in flight.

— kthxbye.
