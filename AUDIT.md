# Night Shift Security — System Audit

**Date:** 2026-06-18
**SPEC:** v5.0.0-draft (pivot from v4.2.0)
**Reference audit:** [`SYSTEM_AUDIT_2026-06-18.md`](SYSTEM_AUDIT_2026-06-18.md)

This audit log now records v4.2.0 closure. The 2026-06-18 system audit (separate file) drove the v5 pivot. All v4.2.0 entries below are historical; submission citations now live in the v5 audit.

## Executive Summary

Night Shift Security v4.2.0 was a gate-heavy adversarial research engine. After the 2026-06-17 run completed 13/13 folds with `submit_ready=0`, a directed audit on 2026-06-18 identified eight structural defects upstream of the gates — the gating, trust boundary, lab notebook, RSI, and skill lockdown remained correct. The substrate (synthetic param-grid engine + catalogue replay + 28-of-249 scope) was the wrong basis for novel bug discovery. v5 pivots to per-target NativeHarness substrate.
**Latest full v4.2 HIPIF run:** 2026-06-17 04:32 UTC, 13/13 HIPIF folds, `gate_ok=true`, `submit_ready=false`, elapsed 3564s; fold summary: scan_all, depth_wormhole (13 findings, 2 fork_repro), kamino_preflight, depth_kamino (39 findings, 108 solana_repro), cantina_slates (9 programs x 3 trials), hunt_rotation, rsi_fold, depth_wormhole_bridge (13 findings, 10 fork_repro), refine_conditional, coordinator_conditional, journal_fold, gate
**Latest full v4.1 HIPIF run:** 2026-06-16, 13/13 HIPIF folds, `gate_ok=true`, `submit_ready=false`, elapsed 4805s
**Sandbox-safe verification:** 438 passed, 5 skipped
**Focused verification:** 66 passed (`test_solodit`, `test_self_interrogation`, `test_validation_layer`, `test_bounty_loop`, `test_pipeline`, `test_structural_filters`); 28 passed (`test_klend_account_discovery`, `test_klend_tx`, `test_klend_live_probes`, `test_klend_harness`, `test_validator_profiles`); 42 passed (`test_wormholescan`, `test_fork`, `test_failure_trace_rsi`, `test_task_verifier`, `test_wormhole_economic`); live Foundry Wormhole value probe 2 passed, 3 optional route replays skipped by default; focused AuditVault corpus integration tests passed

## Executive Summary

Night Shift Security is a gate-heavy adversarial research engine. v4 adds the missing discovery layer: semantic recon, concrete candidate storage, target-pinned proposals, SARIF/static-tool ingestion, fail-closed PoC generation, KLend v2 account/instruction artifacts, Wormhole economic gates, and failure-trace RSI. v4.1 adds deterministic self-interrogation reports before expensive validation lanes. v4.2 adds Solodit corpus sync and an authenticated proposal-generation lane.

The main bottleneck is no longer orchestration. The bottleneck is turning concrete candidates into candidate-specific, value-moving reproductions against real deployed state.

| Metric | Current Value |
|--------|---------------|
| `submit_ready` | 0 |
| Findings store | 54k+ records |
| Improvement ledger | 1.7k+ actions |
| Concrete candidates | 559 Wormhole candidates from semantic recon |
| Self-interrogation | Advisory conviction reports by default; bounty-depth rank pressure enabled |
| Solodit corpus | Deterministic sync + pattern JSONL; proposals are untrusted analogues only |
| AuditVault corpus | Deterministic sync + patterns + summary (2383 findings, 826 slug×id pairs across 533 protocols); advisory analogue intelligence only |
| Agent proposal lane | Optional authenticated xAI-OAuth `hermes chat` turn on `nightsoul`; writes untrusted `auditvault-*.json` proposals (lineage `f60cd87d0758`+`3365e69dc864`, target=wormhole, `token_account_dos`); `metadata.trusted=false`, `severity_score=0.0` |
| Primary cron | `nss-hipif-chain`, daily 04:00, no-agent deterministic |
| `nightsoul` skills | Locked to 20 symlinks (19 NSS canonical + `auditvault-research`) |
| Current Cantina slates | uniswap, reserve-protocol, euler, polymarket, coinbase, morpho, pendle, okx, paxos |

## Current System Map

```text
NightSoul cron 04:00
  -> hermes/scripts/nss-hipif-chain.sh
  -> hermes/scripts/nss-hipif-chain-run.py --phase full
  -> scan_all
  -> Solodit corpus sync / pattern extraction
  -> AuditVault corpus sync / pattern extraction / summary
  -> semantic recon / concrete candidate store
  -> self-interrogation conviction reports
  -> Wormhole depth
  -> KLend live preflight + depth
  -> Cantina slates
  -> fork-ready hunt
  -> recursive improvement
  -> refinement passes
  -> coordinator
  -> lab notebook
  -> HIPIF gate

Optional authenticated follow-up (07:00):
  -> hermes chat --profile nightsoul -s auditvault-research -s solodit-research
  -> xAI-OAuth (grok-4.3, max-turns 25)
  -> writes data/security_results/hermes_proposals/auditvault-*.json (untrusted)
  -> writes data/security_results/lab_notebook/auditvault-agent-*.md
```

Authoritative artifacts:

| Artifact | Path |
|----------|------|
| HIPIF state | `data/security_results/hipif/folded_context.json` |
| Loop state | `data/security_results/loop/state.json` |
| Findings store | `data/security_results/knowledge/findings_store.jsonl` |
| Improvement ledger | `data/security_results/knowledge/improvement_ledger.jsonl` |
| Refinement hints | `data/security_results/loop/refinement_hints.json` |
| Concrete candidates | `data/security_results/knowledge/concrete_candidates.jsonl` |
| Conviction reports | Candidate vector metadata (`self_interrogation`, `conviction_score`, `conviction_action`) |
| Human gate alert | `data/security_results/loop/submission_alert.json` |
| Lab notebook | `data/security_results/lab_notebook/*.md` |

## Strengths

1. Python gates are authoritative; agent output is untrusted.
2. Submission gates now require concrete candidate binding, source commit, selector/discriminator, candidate-specific reproduction artifact, and measured impact.
3. No-agent cron path has been verified to complete 13/13 folds and final gate.
4. Findings are recorded even when nothing is submittable.
5. RSI mutates future work via repeated-fingerprint detection, cooldowns, saturation, scan boosts, refinement queues, config fallbacks, and failure-trace summaries.
6. Self-interrogation now challenges target/source binding, invariant quality, impact, replay risk, and overfitting before costly validation lanes.
7. Cantina target coverage now tracks current high-value opportunities, including dYdX and Paxos metadata.
8. AuditVault and Solodit operate as parallel analogue corpora under identical trust-boundary rules; neither can satisfy evidence or submission gates.
9. `nightsoul` skill surface locked to 20 NSS-v4 symlinks; agent cannot load unrelated skills even if they exist on disk.
10. Trust-boundary integrity verified for the AuditVault path: zero references to `auditvault` or `audit_corpus` inside `submission_gates`, `evidence_grading`, `novel_gate`, `nss-hipif-chain-run.py`, `klend`, `wormhole_economic`, or the fork rejection helpers.

## Current Gaps

| Priority | Gap | Current Evidence / Next Action |
|----------|-----|--------------------------------|
| P0 | No novel `submit_ready` | Correct gate behavior; bind concrete candidates to real state and measured deltas. |
| P0 | KLend value movement missing | KLend oracle borrow now uses source-derived account metas, setup, cloned Scope oracle, validator slot warp, and refresh prelude. It still records zero delta because Scope USDC price/TWAP are too old (`oracle_price_too_old`, reserve price status `00110101`). Next action: fresh oracle-state strategy or a target path not blocked by stale Scope price. |
| P0 | Wormhole economic exploit missing | Live invalid-completion probe confirms zero delta; mocked-authorized baseline moves exactly 1 USDC with matching accounting; real signed native-release and wrapped-mint VAAs verify through live core but are already completed with zero delta. A pending plain payload-id 1 Ethereum-native release completed on fork with matching live-decimal token and outstanding deltas, confirming authorized replay only. Asset-meta replay found same-chain Ethereum metadata and skips before `createWrapped`. Latest 40-page paged corpus scan decoded 718 token-bridge-shaped VAAs with 146 plain Ethereum-native releases, 46 plain Ethereum wrapped mints, 33 Ethereum-native transfer-with-payload routes, 6 Ethereum wrapped-mint transfer-with-payload routes, and 1 same-chain asset metadata route. `HARNESS_AUTH_MOCKED`, `AUTHORIZED_REPLAY`, already-completed replay, transfer-with-payload sender constraints, and same-chain metadata are non-submittable. |
| P1 | Native harness gaps for Cantina | Morpho/Pendle/Uniswap/OKX/Paxos still lean on analogue configs; add native target harnesses. |
| P1 | dYdX unsupported execution lane | Registry tracks dYdX, but default slates exclude it until Cosmos SDK/CometBFT harness exists. |
| P2 | Full runner lacks mock E2E pytest | Add a reduced, mocked end-to-end test for `nss-hipif-chain-run.py --phase full`. |

## Closed Issues

| Issue | Status |
|-------|--------|
| HIPIF fold drift | Fixed. |
| Saturated fork-ready hunt starvation | Fixed with `ignore_saturation`. |
| Agent cron false-pass | Fixed operationally by switching primary cron to no-agent deterministic full runner. |
| Wormhole triage treated as submittable ambiguity | Fixed by explicit v4 economic gate plus failure-trace routing to value-moving PoC generation. |
| Coinbase/Polymarket Cantina using wrong Wormhole config | Fixed with dedicated configs. |
| `nightsoul` skill drift toward unrelated domains | Fixed by locking the profile to 20 symlinks (`hipif`, `bounty-loop`, `recursive-improvement`, `coordinator-cycle`, `lab-notebook`, `hypothesis-expansion`, `immunefi-scan`, `investigate-from-scan`, `novel-vector-digest`, `knowledge-campaign`, `operator-checkpoint`, `operator-submit`, `operator-exploit`, `operator-recon`, `operator-triage`, `solodit-research`, `shoestring-pack`, `day-shift-cycle`, `night-shift-run`, `auditvault-research`); covered by unit test. |
| AuditVault corpus ingest leaking into gates | Fixed by isolating AuditVault to `platform/`, `pipelines/`, `hermes/skills/auditvault-research/`; zero references in `submission_gates`, `evidence_grading`, `novel_gate`, `nss-hipif-chain-run.py`. |

## Submission Gate

`submit_ready` requires all of:

- `qualifies_for_submission() == true`
- evidence grade >= 4
- deployed viable
- non-catalogue
- credible reproduction tier (`fork_reproduced` or `solana_validator`)
- concrete candidate schema >= 4
- source commit and selector/discriminator
- candidate-specific reproduction artifact
- measured non-fee economic impact

Catalogue replay, smoke triage, fee-only CPI, and zero-delta generated PoCs remain research outputs only.

## Next Actions

1. Use Wormholescan real VAA replay plus the live Wormhole USDC accounting baseline to generate non-mocked accounting-violation cases for `completeTransfer*`, `createWrapped`, and wrapped/native accounting.
2. Use conviction reports plus failure signatures to replace KLend fail-closed generated probes with a real value-moving transaction path.
3. Add native Cantina harnesses for Uniswap, Morpho, Pendle, OKX, and Paxos.
4. Add a dYdX/Cosmos execution lane before scheduling dYdX nightly.
5. Add mocked full-chain E2E test coverage for cron regressions.

## v5 Pivot (2026-06-18)

The `SYSTEM_AUDIT_2026-06-18.md` directed audit closed the v4.2.0 path because eight structural defects upstream of the gates prevented novel bug discovery: synthetic param-grid engine, 28-of-249 scope, fork_reproduced aggregator mask, self-saturating loop, lack of native per-program harnesses.

| Action | Status |
|--------|--------|
| Cron paused via `NSS_HIPIF_PAUSE_FOR_NATIVE=1` precondition gate | shipped (C8) |
| `native/__init__.py` + `native status`, `native mark` CLI | shipped |
| 6 native-harness tests passing (`tests/test_native_harness.py`) | shipped |
| SPEC v5.0.0-draft header added | shipped |
| First NativeHarness target = Uniswap v4 ($15.5M Cantina pot) | **harness_built** (2026-06-19) — ABI/selectors bound, StateView.getSlot0 live RPC probe PASS; concrete_candidates.jsonl +66 entries |
| Measured impact oracle | not started (audit C2) |
| Synthetic substrate deprecated under `legacy/synthetic/` | not started (recommendation; do not break 438-test baseline) |

### Current v5 Gaps

| Priority | Gap | Next Action |
|----------|-----|-------------|
| P0 | First measured delta on a real contract | Foundry test under `foundry/test/UniswapV4*.t.sol` that calls live PoolManager and snapshots pre/post balances (Ready status wait): C2 MeasuredImpactOracle |
| P1 | Measured impact oracle module | C2 from audit; wire into `validation/submission_gates._v4_candidate_submission_ok` |
| P1 | Loop precondition guard | C3 audit — `pick_next_target` should refuse slugs without populated `concrete_candidates.jsonl` and harness entry |
| P2 | Synthetic substrate deprecation | Move legacy param-grid/CPCV paths under `legacy/synthetic/`, retain for regression fixtures |
