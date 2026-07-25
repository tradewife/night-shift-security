# Next session queue

**Rootstock PowPeg: strategy orchestrator + parallel harness execution. 1inch Smart Contracts: sessions 1–8 honest-zero. Horizen: Phase B re-eval 2026-07-27. submit_ready=0.**

> **Cross-target closeout (2026-07-26 — v6.61.0, Rootstock PowPeg onboarding):**
> Rootstock PowPeg onboarding complete. rsk-powhsm@5.6.2, powpeg-node@VETIVER-9.0.3.0, rskj@VETIVER-9.0.3. Quarkslab SGX audit (9 findings) mapped. Codegraph-x-ray on Primary Subsystem (bc_advance+auth_tx+attestation+upgrade+Java signer) delivered 30 invariants + 22 property candidates + 9 strategies (≥70% Primary). Minimal harnesses built: C libFuzzer (bc_advance), Python (attestation middleware), Java JQF differential (signer message builder). rskj Bridge precompile codegraph (108 symbols). **submit_ready=0** — honest-zero start.
> Local artifacts only: `data/security_results/investigations/2026-07-25-rootstock-powpeg/`, `sources/rsk-powhsm/firmware/fuzz/`, `sources/powpeg-node/src/test/.../PowHSMSignerMessageBuilderDifferentialFuzzTest.java`.

> **Prior closeout (2026-07-25 — v6.60.2, Horizen Session 3):**
> Extended 4d-chess-sequential press closed: ~90+ NSS tests R3–R26, live mainnet pre-flush +
> testnet post-flush, frontend/subgraph/OFT/Binary. **submit_ready=0.** FINDING-001 refined
> (mid-stream dust blends). Investigation + harnesses **keep-local** per AGENTS.md.
>
> **Horizen plan (ordered):**
> 1. **Phase B re-evaluation 2026-07-27 (mandatory)** — Immunefi scope/reward/config deltas only.
> 2. **First-flush live check** — when `data/security_results/investigations/2026-07-24-horizen-zen-staking/watch-first-flush.sh` reports `POST_FIRST_FLUSH`, re-run `NSSRound22FirstFlushFork` / claim-all solvent. MEV/capital share is not a bug.
> 3. **Do not** re-invest in RA core, OFT token, or Identity EP without a new surface.
> 4. Optional low-pri: subgraph sticky-owner mapping note (informational only; not fund theft).
>
> **Primary open track** remains the Rootstock PowPeg arc below.

## Priority 0 — Rootstock PowPeg strategy execution

1. Run `agentic-strategy-generation` → `strategy-orchestrator` with property candidates from `invariants.md` + `property_candidates.md`.
2. Execute harnesses in parallel on Primary Subsystem:
   - C libFuzzer (bc_advance) — `sources/rsk-powhsm/firmware/fuzz/fuzz_bc_advance.c`
   - Python adversarial TCB (attestation middleware) — `sources/rsk-powhsm/firmware/fuzz/fuzz_attestation_middleware.py`
   - Java JQF differential (signer message builder) — `sources/powpeg-node/src/test/java/.../PowHSMSignerMessageBuilderDifferentialFuzzTest.java`
3. Promising candidate: PROP-BC-001 (brother MMP skip) with test 107 seed corpus.
4. rskj Bridge precompile: deep-dive on `Bridge.execute()` + `BridgeSupport` invariants.

## Priority 1 — 1inch Smart Contracts arc (resume)

1. Full `4d-chess-sequential` on **LOP NativeOrder** (`NativeOrderFactory` / `NativeOrderImpl`).
2. Mainnet fork Settlement + live fill path if RPC.
3. Permit2Proxy makerAssetSuffix assembly.

## Already exhausted (skip re-run)

- Cross-chain escrow (EVM/Solana/Fusion) — sessions 1–5
- Farming ∩ Token-hooks — session 6
- Delegation — session 7
- limit-order-settlement surplus/whitelist/Kyc/priority — session 8 (32/32)
- **Horizen RA ↔ ZenStaker primary + Session 3 extended press** — v6.59.0–v6.60.2 (honest-zero)

## Priority 2

SDK E2E / Crucible / other 1inch scope expansion.
