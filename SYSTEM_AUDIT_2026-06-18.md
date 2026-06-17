# Night Shift Security — System Audit

**Date:** 2026-06-18
**Auditor:** Codex pre-implementation design pass
**Scope:** Why v4.2.0 has produced 0 submissions on every full HIPIF run
**Outcome:** Eight structural defects, one wrong goal model. Recommendations below.

---

## Executive diagnosis (read this first)

The system is functioning precisely as designed. **The design is wrong for the stated goal.** We have built a high-quality **catalogue replay / synthetic regression engine** and labeled it an **adversarial research engine for novel bounties**. The gates correctly reject every finding because every finding is, by construction, either a rediscovery of a historical exploit played against a synthetic `ContractState` or a "triage surface" probe that measures no on-chain delta.

The SPEC is honest about this in §4 root-cause findings F1–F6 — and acknowledges in §21 / §25 that "shipped" does not equal "submittable." But the SPEC still treats this as the **final state** rather than the **initial baseline** of a different architecture. None of the workstreams defined in §7–§14 directly attack the core defect: *the engine never reads deployed contract bytecode/IDL/storage layout in a way that generates a sequence of state-changing calls against real on-chain state.*

We can keep all the existing gates, all the trust-boundary rules, and all the lab-notebook discipline — they are correct. We must replace the discovery substrate.

---

## Where the gap lives, in the code

| Layer | Effect | Evidence |
|-------|--------|----------|
| `domain/attack_hypotheses/parameter_spaces.py` | Defines 7 abstract float/choice parameter spaces (`loan_fraction_of_ceiling`, `oracle_dependency_score`, `recursion_intensity`, `chain_depth`, `role_bypass_severity`, ...). None of these names appear in any real contract. | The space definitions have no `entrypoint`, no `selector`, no `account`, no `storage_slot`, no `token_mint`, no `program_id`. |
| `domain/attack_templates/*.py` | Each template inspects `ContractState` synthetic fields (`treasury_balance_usd`, `attacker_voting_power`, `callback_enabled`, `oracle_dependency`). It then **simulates** a numeric outcome (`extracted = min(borrow_capacity * 0.6, treasury_balance_usd)`). | `composability_risk.py` line 60–80 is representative. |
| `data/exploit_catalog.py` | Precomputed historical exploits store `known_parameters` and synthetic `ContractState` per exploit. The engine's only contract "knowledge" comes from this 19-row, hardcoded list. |
| `core/hypothesis.py + target_harness.py` | Vectors are `grid_combos(template.param_grid())` * N samples. `evaluate_target_vectors` then runs each vector against a synth state and `evm_fork_targets()`-mock pins onto historical blocks. |
| `core/pipeline.py` | Pipeline stages are stubs relative to live targets: `run_fork_validation_phase` only fires a Foundry test against an `euler-finance-2023` (precomputed) or `nomad-bridge-2022` fork. Non-anchor candidates fall through to `_apply_evidence_grade_scoring` based on simulation outcomes. |
| `validation/fork_validation.py` `_fork_candidate_set` | When `always_test_catalog_evm_anchors: true` (the default for every EVM bounty program), the only candidates that reach `forge test` are those whose `catalog_exploit_id` exactly matches a hardcoded anchor. The rest never see `forge` at all. |
| `validation/solana_validation.py` (KLend) | Probe matrix is hardcoded `pseudo-instruction prefixes` (still partially hardcoded per AUDIT §F5). Fee-only CPI > 0 lamports is the only meaningful measurement. |
| `bounty/discovery_scan.py` `scan_program` + `_sort_scan_results` | Scan synthesises 73 candidates per program in pure zero-RPC mode; ranks by synthetic `severity_score` + `best_evidence_grade`. `submission_ready: false` is correct because no fork was actually run. |
| `bounty/loop.py` `_maybe_mark_saturated` | After one cycle, a target is marked `saturated` if **all** findings are `catalog_analogue`. So: every Cantina/Immunefi target the loop picks immediately enrolls in `saturated_slugs`. 12 are saturated as of 2026-06-16. |
| `bounty/loop.py` `pick_next_target` | `pick_investigation_targets` filters by `best_evidence_grade` (always passes in zero-RPC mode because scan synthesises grade 4) and removes excluded/saturated slugs. The system ends up running the same 9–12 programs every cycle, with no native harness for any of them. |

**Net result**: 54k+ findings in `findings_store.jsonl`, ~187 findings per run, every one either a synthetic rediscovery or a triage probe, **all gated down to `submit_ready=0`**. The lab notebook is honest about it. The SPEC is honest about it. The gates are correct. None of this is a bug — it is the design.

---

## Why the system thinks it is making progress

1. **Saturated slugs grow.** 12 targets saturated means 12 "we tried them." RSI queues `refine_conditional` for them, then they get re-tried with the same synthetic catalog vector set.
2. **Self-interrogation validates what's already abstract.** Reports are correctly advisory; conviction reports describe families of synthetic params, not specific contracts.
3. **Solodit / AuditVault corpora ingest correctly** but pipe into a synthetic scoring layer. They enrich *seed analogues*, not probe paths.
4. **`fork_reproduced` counts inflate the success signal.** Reading the latest run's `findings.json`: every single finding has `"fork_reproduced": false` and `method: catalog_fallback`. The "98 fork repros" in the post-run tally are catalog-fallback coverage, not mainnet forks against the targeted program.
5. **`solana_reproduced: 107` for kamino** is the fixture harness; AUDIT and SPEC confirm fee-only CPI is the entire observed outcome.

The metric we report back to ourselves ("13/13 folds, gate_ok=true, 108 solana repros, 98 fork repros") is structurally meaningless relative to the goal of "submit a legitimate bug."

---

## Eight structural defects we need to fix

### D1. **Fake scope - the engine operates on 28 hand-picked programs out of 249.**
- `platform/sync.py` writes `scope_registry.json` with 249 entries (213 Immunefi + 36 Cantina). Only 28 are "curated." `bounty/discovery_scan.scan_program` iterates `list_programs_for_platform` which only returns the curated 28.
- **Fix:** expand `IMMUNEFI_PROGRAMS` and `CANTINA_PROGRAMS` to all live, non-deposit-or-zero-TV programs, and let `scope_registry` drive the iteration. Most Immunefi programs are not in `IMMUNEFI_PROGRAMS` at all (Aevo, Aave, Ankr, Lido, MakerDAO, Compound v3, Curve, Convex, Balancer, etc.). Their $5M–$15M bug bounty pots are **the entire prize pool** of this work.

### D2. **Fake harness - zero native programs actually run.**
- Only Wormhole has any native harness. There is no real Uniswap/Uniswap-v4 hook, no Compound v3, no Morpho Blue, no Pendle PT, no Euler v2, no Sky/Maker, no Aave v3, no Curve, no Convex, no real SOUND/Blackhole/Element/Resolv/etc. cantina target.
- Each of those protocols has **public ABI/IDL + mainnet deployment addresses + working invocations**. These are *not* research projects; they are engineering projects that take ~1 day each to wire up.
- **Fix:** Build a **NativeTargetHarness** per program: ABI/IDL fetch + function selectors/instruction discriminators + account resolution + fork-bound tx stub + invariant template. Use the cantina bid amounts as the priority queue (Uniswap $15.5M > Liquid Collective > ...). This is the single biggest unlock.

### D3. **Fake impact oracle.**
- `domain/attack_templates/*.py` writes `economic_impact_usd = min(borrow_capacity * 0.6, treasury_balance_usd)` — synthetic numerics. There is no measured oracle for "this actually moves money."
- **Fix:** A `MeasuredImpactOracle` that on a successful fork run does the actual `(pre_balance, post_balance)` diff on (a) `treasury`/`vault`/`reserve`/token-vault addresses; (b) attacker EOA; (c) `outstanding_bridged(...)` style accounting. Wormhole value probe code already does this. Use it everywhere.

### D4. **Concrete candidate schema is shipped but never populated from real state.**
- `knowledge/concrete_candidates.jsonl` is meant to store `{entrypoint, selector_or_discriminator, sequence, accounts, impact_oracle}`. Currently it is **populated only by Wormhole semantic recon (559 entries on wormhole repo commit)**. Nothing else gets in. SPEC §6 says "must be target-pinned" but the operational path to generate candidates for Morpho/Pendle/Euler/Uniswap fails because no native target harness exists.
- **Fix:** the same `semantic_recon()` workflow that extracted 606 Wormhole entrypoints must be run against every protocol's main repo (`sources/<slug>/repo`). The candidate-population gate becomes: "no concrete candidate in the store => cannot target."

### D5. **`saturated_slugs` + `pick_investigation_targets` lock the loop into the same 9–12 programs.**
- Even if we add 100 real programs, the loop will perpetually return the same 12 due to `summarize_failure_traces(...).stop_trials -> saturate_slug`, "all-analogue → saturated," and `NSS_LOOP_DEPTH_SLUG` pinning.
- **Fix:** Add a **target budget** that mandates 80% of compute to **unsaturated, unranked, unproven targets** ("discovery mode") and only 20% to depth of known analogues. RSI saturation fix must be opt-out only when there are no candidates left in the global queue.

### D6. **Hypothesis generator is generic-by-construction.**
- `parameter_spaces.py` sample spaces are reusable param grids divorced from any protocol. SPEC §F1 called this out. The fix isn't "more samples" — it's schema level per-target.
- **Fix:** Introduce per-target hypothesis generators that read `concrete_candidates.jsonl` and emit `seq=call(deposit,USDC,X); call(borrow,USDC,Y); check(pre_bal-vault, post_bal-vault)` style sequences. Use Foundry cheatcode `vm.deal` / `deal(token)` to seed funds, real ABI calls. This is what `pocgen` was supposed to do (SPEC §10, workstream D); it shipped but ran once against Wormhole.

### D7. **Cron architecture concentrates compute where there's no harness.**
- The 04:00 cron runs `nss-hipif-chain.sh` → `nss-hipif-chain-run.py` → 12 trials wormhole + 5 kamino + 9 cantina each ×3 + 4 hunt ×3 + 4 bridge ×3 + 3 refine ×2 + 2 coord cycles. That's 84+ loop iterations/week on **the same Wormhole/Kamino/Cantina/itinerant set**, 0 on the 230+ other live Immunefi/Cantina programs.
- **Fix:** The cron should: (a) hit `platform/sync.py` first to refresh both registries; (b) compute new unsaturation; (c) hand out one **new target per nightly run** (a fresh program from the full registry) for full native harness build + first candidate generation. Reserve Wormhole/Kamino depth passes for *after* at least one new target has been on-ramped.

### D8. **`fork_reproduced` aggregator lies about what worked.**
- `run_fork_validation_phase` `fork_confirmed = max(fork_anchor_result, top_n_severity_result)`. A severity-0.91 simulation finding for `nomad-bridge-2022` marked `fork_reproduced: false` still gets rolled up into "fork_reproduced: N" tallies. Lab notebook reports reflect that, operators see numbers that suggest progress.
- **Fix:** Fork tallies must distinguish `{catalog_anchor_fork, live_program_fork, value_moving_fork, novel_fork_reproduced}` explicitly. Operators must see "98 catalog-anchor" vs "0 live-program fork" when reading a run summary. This is a 30-line change in `bounty_loop._record_run` + `recursive_improvement`.

---

## The wrong goal model

Current implicit goal: **"run as many canonical exploits as possible through the deterministic chain and keep the gates clean."** Visible in: SPEC §25 says "0 submit_ready is acceptable if gates are blocking weak evidence"; saturated slugs grow; `auditvault_*` ingest is the latest substantive workstream.

Real goal: **"submit at least one legitimate bug to a live Immunefi or Cantina program."** That goal requires:

- (1) bind to a real deployed protocol,
- (2) execute real state-changing calls,
- (3) measure real on-chain delta,
- (4) verify root cause from deployed bytecode/IDL (not catalogue stub),
- (5) write a PoC a triager can run.

None of these five requirements are powered by the synthetic `ContractState`/param-grid engine at the heart of `core/hypothesis` + `core/target_harness`. They are powered by **Wormhole's semantic recon + value probe** — and we did not extend that harness anywhere.

---

## Recommended action plan

### Phase 1 — Re-orient (this session)

1. Update `day_shift/current.md` and `AUDIT.md` to record: "v4.2.0 architecture is faithful but the substrate is wrong; new direction: native per-program harnesses for top-$ Immunefi/Cantina targets."
2. Stop the nightly cron for two days; do not run another HIPIF chain until at least one new harness is built and one new program can be tested against live mainnet state.
3. Add pre-flight checks in `bounty_loop.py`: `pick_next_target` should refuse to enqueue any slug whose `concrete_candidates.jsonl` size is `< 50` *or* whose native harness status is `"missing"` in `data/security_results/loop/native_harness_status.json`. This prevents the loop from running the same synthetic engine on Morpho for the nth time.

### Phase 2 — First native harness (this week)

Pick **one** high-value, well-instrumented EVM target. Recommended: **Uniswap v4 (or Aave v3)** because they have:
- public ABI, deployed address, working forks on every RPC,
- a documented upgrade + hook architecture (massive novel surface),
- a $15M cap and an established Cantina contact.

Steps:
1. `git clone https://github.com/Uniswap/v4-core sources/uniswap_v4/repo`
2. Run `semantic map --slug uniswap_v4 --repo sources/uniswap_v4/repo --kind amm` to populate entrypoints, call graph, and `concrete_candidates.jsonl`.
3. Build `src/night_shift_security/native/uniswap_v4.py`: ABI loader, `PoolManager` selectors, `modifyLiquidity`/`swap`/`donate` flow probe, settled `PoolKey` storage layout, `BalanceDelta` deltas, and a Foundry-harness test under `foundry/test/UniswapV4*.t.sol` that actually calls into the deployed `PoolManager`.
4. Wire `fork_target` registry → `candidate_schema_v4` → `MeasuredImpactOracle` to PoolManager's ETH/USDC/USDT pool balances.
5. Run one loop iteration; require balance delta to flip submit_ready.

Aave v3, Morpho Blue, Pendle, Euler v2, and Euler v2 hookslayer all fit the same shape.

### Phase 3 — Scale (next 2–3 weeks)

Once one harness lands, build the next five by template:

| Target | Why | Native entrypoints |
|--------|-----|--------------------|
| Aave v3 | Real lending: borrow/liquidation/repay across reserves | LendingPool + PoolDataProvider + Oracle reads |
| Morpho Blue | Minimal lending: matchBorrow/withdraw/claim, oracle check | Morpho Blue core, OracleLib, IRM |
| Pendle PT | Yield tokens: redeem/redeemDue/OneSide, PT/YT redeem | PendleRouter + Market + Oracle |
| Compound v3 | Comet: supply/withdraw/absorb/buyCollateral | CometProxy, CometStorage, Configurator, BulletRepay |
| Curve/StableSwap | Add/remove liquidity, exchange with custom D | triCrypto/StableSwap pool ABIs + views |

For each, the same path: clone repo + semantic recon + native harness + v4 candidates + measured oracle.

### Phase 4 — Reinstate the cron with new precondition gates

`nss-hipif-chain-run.py`:

- Each cycle, before any bounty_depth pass, run `platform sync` (immunefi + cantina) and emit fresh scope_registry.
- Re-target criterion: **first must-pop is the program with the largest `max_bounty_usd` that has not been touched in 14 days and has a populated `concrete_candidates.jsonl`**.
- `saturation` rule must rotate out of "all findings are catalog analogue" to "all findings are catalog analogue AND no native program deployed-states have been bound since saturation."

---

## Recommended corrections (concrete, code-level)

| # | Change | Why | Effort |
|---|--------|-----|--------|
| **C1** | New file: `src/night_shift_security/native/harness.py` defining a `NativeHarness` protocol: ABI fetch, selector decoding, account resolution, tx-stub builder. First impl: `native/uniswap_v4.py`. | Concrete candidate schemas are unblockable. | ~3–5 days |
| **C2** | New file: `src/night_shift_security/impact/measured_oracle.py` — `(pre_state, post_state, deltas)` measured-oracle; integration in `validation/submission_gates.py._v4_candidate_submission_ok`. | Triage-surface gates stop accepting zero-delta. | ~1 day |
| **C3** | Patch `bounty_loop.pick_next_target`: require `native_harness_status.json` entry per slug; skip otherwise. | Stop looping on programs without substrate. | ~0.5 day |
| **C4** | Patch `recursive_improvement._maybe_mark_saturated`: don't add new saturated when >=1 candidate has measured delta outside catalogue analogue. | Allow continued depth on native-bound programs. | ~0.5 day |
| **C5** | Patch `run_bounty_scan` to walk the full live registry (immunefi+cantina), not curated. | Discover targets the operator forgot. | ~1 day |
| **C6** | Patch fork_validation `_fork_candidate_set` to require a real ABI or IDL hash on top-N (not severity). | Stop hard catalog-only forks. | ~1 day |
| **C7** | Diff the run summary's `fork_reproduced` breakdown into `{catalog_anchor, live_program, value_moving, novel}`. | Fix the metric that misleads operators. | ~0.5 day |
| **C8** | Add a precondition gate to `nss-hipif-chain.sh` (and `nss-hipif-chain-run.py:_run_full_chain`): refuse to run if `uncovered_native_targets > 0` and recent native-harness builds < 1. | Force the cron into harnessing instead of running the same Loop. | ~0.5 day |
| **C9** | Open `day_shift/open.md` task: "First native-harness build — pick a target and fork it." | Reset Day Shift's focus. | text only |

---

## What does *not* need to change

- The Python authority gates (`submission_gates.py`, `evidence_grading.py`, `task_verifier.py`) are correct. Do not relax them.
- The `metadata.trusted=false` discipline is correct. AuditVault and Solodit being advisory-only is correct.
- Self-interrogation, RSI, refinement_hints, failure_signatures: all correct loop primitives; they need *different inputs* (real candidates), not different machinery.
- `nightsoul` skill lockdown to 20 symlinks + agent lane restricted to `nightsoul`: keep. Anti-skill-drift is correct.
- The lab notebook + chain-state fold discipline is the right substrate for letting Day Shift steer Night Shift — keep.

---

## Bottom line

The gating is doing exactly what the spec asked. The problem is upstream of the gating: there is nothing real to gate. The fix is a one-week pivot from "more synthetic trials through cleaner gates" to "build one real on-chain harness, prove one measured delta, then build four more." Every chronic symptom —fee-only CPI for KLend, triage-surface `triage_surface_verified=false` for Wormhole, $0 economic moves everywhere, 12 saturated slugs and growing — dissolves once a real harness exists because the synthetic engine has nothing to latch onto.

Concretely, the path is:

1. Stop running the cron in its current form (C8).
2. Build a `NativeHarness` for one high-value program (C1).
3. Ship a single submittable test of that program (C2 + measurement).
4. Repeat for 4–5 more targets (Compound v3, Aave v3, Morpho Blue, Pendle, Euler v2).
5. Then the gates stop being aspirational.
