# Night Shift Security — Adversarial Research Architecture

**Version:** v4.0.0  
**Date:** 2026-06-15  
**Status:** Current architecture baseline

## Intent

Night Shift Security is a programmable adversarial research engine for DeFi and protocol bounty work. It searches for attack candidates, validates them through statistical and execution gates, records all findings, and promotes only human-gated, reproducible, non-catalogue, value-moving results.

The v4 architectural shift is from broad generic trials to source-grounded semantic discovery.

## Layers

| Layer | Name | Responsibility |
|-------|------|----------------|
| 1 | Target Intelligence | Platform sync, curated registries, bounty scope, cloned repos |
| 2 | Semantic Discovery | Entry points, authority graphs, value flows, bridge/oracle surfaces, candidate seeds |
| 3 | Hypothesis Search | Templates, Darwinian mutation, target-pinned proposals, bounded LLM assistance |
| 4 | Execution Harnesses | Foundry forks, Solana validator/KLend, generated fail-closed PoCs, static-tool ingestion |
| 5 | Validation Gates | MC, CPCV/PBO, evidence grading, task verifier, credible harness gate |
| 6 | Promotion / Export | Bounty scoring, `research` vs `submittable`, IVSS, human gate |
| 7 | Orchestration / Memory | HIPIF, bounty loop, RSI, Coordinator, lab notebook, findings store |

## Primary Night Chain

The production nightly path is no-agent and deterministic:

```bash
NSS_HIPIF_MODE=deterministic hermes/scripts/nss-hipif-chain.sh
```

It runs:

```text
scan_all
-> Wormhole semantic recon / concrete candidates
-> depth_wormhole
-> kamino_preflight
-> depth_kamino
-> cantina_slates
-> hunt_rotation
-> rsi_fold
-> depth_wormhole_bridge
-> refine_conditional
-> coordinator_conditional
-> journal_fold
-> gate
```

Cron owner on this machine: `nightsoul`, job `nss-hipif-chain`, daily 04:00, no-agent mode.

## Trust Boundary

- Agents and delegates may propose but never validate.
- Python gates are authoritative.
- `submission_alert.json` is the only external-post trigger and still requires human approval.
- Catalogue replay, triage smoke, fee-only CPI, and zero-delta PoCs cannot become submittable.

## Knowledge Loops

| Loop | Artifact | Purpose |
|------|----------|---------|
| Findings store | `knowledge/findings_store.jsonl` | Append run findings and lineage |
| Candidate store | `knowledge/concrete_candidates.jsonl` | Persist v4 source-bound candidates |
| RSI ledger | `knowledge/improvement_ledger.jsonl` | Record deterministic improvement actions |
| Refinement hints | `loop/refinement_hints.json` | Feed next target/template/proposal pass |
| Failure signatures | `knowledge/failure_signatures.jsonl` | Classify verifier failures into next actions |

RSI actions include repeated-fingerprint detection, cooldown bumps, saturation, refinement queue inserts, scan boosts, template plateaus, config fallback hints, and failure-trace recommendations.

## Current Target Surfaces

| Target Group | Current Support |
|--------------|-----------------|
| Wormhole | Semantic recon, core/token_bridge triage, economic gates, Foundry fork paths |
| Kamino KLend | Live preflight, v2 discriminators, typed account roles, validator/CPI probes |
| Cantina EVM | Uniswap, Reserve, Euler, Polymarket, Coinbase, Morpho, Pendle, OKX, Paxos in default slates |
| Cantina dYdX | Tracked in registry, excluded from default slates until Cosmos harness exists |
| Static tools | Opengrep/SARIF ingestion into candidate store |

## Promotion Criteria

A finding can leave `research` only if it has:

- concrete target binding,
- source commit/provenance,
- selector/discriminator or instruction binding,
- candidate-specific reproduction artifact,
- deployed viability,
- non-catalogue status,
- evidence grade >= 4,
- measured non-fee economic impact,
- `qualifies_for_submission() == true`.

## Priorities

1. Bind top Wormhole candidates to value-moving bridge/core assertions.
2. Turn KLend live reproduction into a non-fee protocol delta.
3. Add native harnesses for current Cantina targets instead of analogue-only fork coverage.
4. Add Cosmos SDK/CometBFT lane for dYdX.
5. Keep no-agent cron gate as the production nightly path; use agent/Hermes only for proposal generation and manual investigation.
