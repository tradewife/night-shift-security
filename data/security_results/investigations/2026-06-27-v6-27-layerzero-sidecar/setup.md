# LayerZero V2 Sidecar Setup — v6.27.0-session30

**Captured at:** 2026-06-27
**Phase:** Phase 1 hard-first only (EndpointV2 + SendUln302 + ReceiveUln302 on Ethereum + 1 L2)
**Sidecar root:** `data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/`

## 1. Bounty & scope recap

- **Immunefi LayerZero omnichain messaging bounty** — max $15M critical, 10% funds-at-risk; V2 contract-specific cap $2M. Group 1 chains (Ethereum, Arbitrum, Base, Optimism, Polygon, etc.) min $250k; Group 2 min $25k.
- **Triaged by Immunefi.** KYC required (operator readiness flagged, not gating). PoC required. Audits-repo items explicitly ineligible.
- **Hard-first scope (Phase 1 only):** EndpointV2 + SendUln302 + ReceiveUln302. OFT/Solana/V1/Aptos deferred to Phase 2A contingent on engine-level signals.

## 2. Source pin

| Tier | Path | Commit pinned | Source-of-truth sha256 |
|------|------|---------------|------------------------|
| Source clone | `sources/layerzero/repo` | `0990059e3ee61ea95f45011cf7284243531fb4c3` (`audit` tag) | README + 197 .sol files |
| Packaged manifest | `sources/layerzero/source_manifest.json` | matches above | EndpointV2.sol = 970208… SendUln302 = bd198e… ReceiveUln302 = 71f8b9… |
| Bytecode pins | `sources/layerzero/bytecode_manifest.json` | pending live RPC fetch (out-of-band) | fields pinned in schema but empty (cannot be filled without ETHEREUM_RPC_URL) |

The `audit` tag is the canonical freeze of the DeFi V2 messaging stack:
- `protocol/contracts/EndpointV2.sol` — LayerZero V2 Endpoint, complete MessagingChannel + MessageLibManager + MessagingComposer + MessagingContext inheritance hierarchy.
- `messagelib/contracts/uln/uln302/{SendUln302,ReceiveUln302}.sol` — DLN-style ULN base classes built on `SendUlnBase` + `ReceiveUlnBase` (DVN-based verification).
- `messagelib/contracts/{Executor,DVN,PriceFeed,Treasury,Worker}.sol` and adapters — sibling surface.

The src compilation at audit-tag is `solc ^0.8.20`. Repo foundry config is per-package — no global library install needed for our falsifier harnesses, which use pure codec + keccak instead of importing the upstream contracts directly.

## 3. Artifact layout (Phase 1 close)

```
data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/
├─ setup.md                    <- this file
├─ property_fanin.md           <- canonical PROP-PKT-001..007 table
├─ strategies/
│  ├─ dvn-positive-negative.md
│  ├─ executor-privilege-escalation.md
│  ├─ message-lib-migration-edge.md
│  └─ (3-strategy fan-out)
├─ runs.jsonl                  <- Ultrafuzz-style attempt log (3 runs)
├─ summary.json                <- Phase-1 close status
├─ adjudication/               <- per-discovery classification
├─ evidence/                   <- preserved crash/repro outputs

sources/layerzero/
├─ source_manifest.json
├─ bytecode_manifest.json
└─ repo/                       <- sparse LayerZero-v2 clone (gitignored)

foundry/test/
├─ LayerZeroEndpointHarness.t.sol
└─ LayerZeroULN302LifecycleFalsifier.t.sol

src/night_shift_security/native/layerzero.py
tests/test_native_layerzero.py
```

## 4. Engine-level posture after Phase-1 round 1

| Substrate | Designed-for | Reach |
|-----------|--------------|-------|
| Foundry `forge build` | codec-level falsifiers + selector sanity | REACHED. Exit 0. No errors. |
| Foundry `forge test (no fork)` | 8 packet-codec invariants | ALL PASS. |
| Foundry `forge test (ETHEREUM_RPC mode)` | bytecode existence + lib getters | DEFERRED to a real-RPC environment. |
| Python `pytest test_native_layerzero.py` | source-pinned resolver + selectors | REACHED. 17/17 PASS. |

The Phase-1 engine-3rd-attempt was a clean **honest-zero candidate**: no invariant violated, no measurable mainnet impact, no candidate classes promoted to `submit_ready`.

## 5. Mandatory Falsification Protocol status

Per SPEC §3.2 + lab notebook `2026-06-20-session-5-calibration-ethena-nonce-collision.md`:

1. **Honest attacker pass on a falsifiable subset:** the falsifiers in `LayerZeroULN302LifecycleFalsifier.t.sol` directly probe the messiest invariant (`_assertAtLeastOneDVN`), the packet-header codec bindings, and the nonce-bucket separation — all pass on the canonical inputs.
2. **Engine-reachability confirmed at the codec layer.** Concrete forged-vector passes (e.g., DVN confirmation overwrite by malicious DVN) are folded into strategy files; their executable escalations (`forge-std` seeks via fuzzer prefix) require library install of `LayerZero-v2` and **deferred to a Phase 2 contingent run** with full source-library integration.
3. **Audit-saturation framing remains bounded.** This Phase-1 hardening project delivers the **4th empirical-FNR datapoint** (after Ethena + Marginfi + Kamino v6.3 multi-attempt). All four are honest-zero; saturation is bounded, not asserted.

## 6. Promotion criteria for any submission candidate

From `src/night_shift_security/validation/submission_gates.py`:

- `score.submission_recommendation == "submit_now"` (engine gates + impact sizing)
- `grade >= 4` (evidence grading)
- `tier in ("fork_reproduced", "solana_validator")` — for EVM contracts, **fork_reproduced** requires a `forge test --fork-url <live RPC>` pass that emits a measurable DELTA_WEI/IMPACT_USD>0.
- `not finding.catalog_analogue` — cross-check vs. known audits repo (Code4rena 2026-04, prior Solodit findings).
- `finding.deployed_viable` — bytecode pin comparison against the deployed `0x1a440…728c` etc.
- **`finding_has_credible_reproduction()`** + **`finding_balance_verified()`** — task verifier + balance delta not zero.
- `_wormhole_submission_ok()` (wormhole-specific gate, irrelevant here).
- `_v4_candidate_submission_ok()` — requires source-pinned schema v4+
- **Human gate** — operator-checkpoint + manual review per `hermes/SOUL.md`.

Phase 1 has **none** of these. Status remains `submit_ready = 0`.

## 7. Hard cutoffs and sidecar etiquette

- Never modify `data/security_results/day_shift/{current,next}.md`.
- Status of this sidecar is tracked in `data/security_results/day_shift/layerzero_sidecar.md` (separate doc).
- Investigation workspace is gitignored by default; only the SPEC + CHANGELOG + day_shift status doc are push-by-default.
- No published candidate without `qualifies_for_submission()` green, no external post.
- No Phase 2A expansions before Phase 1 close.
