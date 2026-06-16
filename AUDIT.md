# Night Shift Security — System Audit

**Date:** 2026-06-17
**SPEC:** v4.2.0
**Current mode:** `nightsoul` cron, no-agent deterministic full v4.2 runner
**Latest full run:** 2026-06-16, 13/13 HIPIF folds, `gate_ok=true`, `submit_ready=false`, elapsed 4805s
**Sandbox-safe verification:** 416 passed, 5 skipped
**Focused verification:** 66 passed (`test_solodit`, `test_self_interrogation`, `test_validation_layer`, `test_bounty_loop`, `test_pipeline`, `test_structural_filters`); 28 passed (`test_klend_account_discovery`, `test_klend_tx`, `test_klend_live_probes`, `test_klend_harness`, `test_validator_profiles`); 40 passed (`test_wormholescan`, `test_fork`, `test_failure_trace_rsi`, `test_task_verifier`, `test_wormhole_economic`); live Foundry Wormhole value probe 2 passed, 3 optional route replays skipped by default

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
| Primary cron | `nss-hipif-chain`, daily 04:00, no-agent deterministic |
| Current Cantina slates | uniswap, reserve-protocol, euler, polymarket, coinbase, morpho, pendle, okx, paxos |

## Current System Map

```text
NightSoul cron 04:00
  -> hermes/scripts/nss-hipif-chain.sh
  -> hermes/scripts/nss-hipif-chain-run.py --phase full
  -> scan_all
  -> Solodit corpus sync / pattern extraction
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

## Current Gaps

| Priority | Gap | Current Evidence / Next Action |
|----------|-----|--------------------------------|
| P0 | No novel `submit_ready` | Correct gate behavior; bind concrete candidates to real state and measured deltas. |
| P0 | KLend value movement missing | KLend oracle borrow now uses source-derived account metas, setup, cloned Scope oracle, validator slot warp, and refresh prelude. It still records zero delta because Scope USDC price/TWAP are too old (`oracle_price_too_old`, reserve price status `00110101`). Next action: fresh oracle-state strategy or a target path not blocked by stale Scope price. |
| P0 | Wormhole economic exploit missing | Live invalid-completion probe confirms zero delta; mocked-authorized baseline moves exactly 1 USDC with matching accounting; real signed native-release and wrapped-mint VAAs verify through live core but are already completed with zero delta. Asset-meta replay found same-chain Ethereum metadata and skips before `createWrapped`. Latest 40-page paged corpus scan decoded 718 token-bridge-shaped VAAs with 146 plain Ethereum-native releases, 46 plain Ethereum wrapped mints, 33 Ethereum-native transfer-with-payload routes, 6 Ethereum wrapped-mint transfer-with-payload routes, and 1 same-chain asset metadata route. `HARNESS_AUTH_MOCKED`, `AUTHORIZED_REPLAY`, already-completed replay, transfer-with-payload sender constraints, and same-chain metadata are non-submittable. |
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
