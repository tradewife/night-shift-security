# Night Shift Security - Technical Specification

**Version:** 5.0.0-draft
**Date:** 2026-06-18
**Author:** Codex pivot pass for Kate / tradewife
**Status:** Pivot to native-harness substrate (v5). v4.2.0 gates/lab-notebook/operator discipline preserved; the synthetic param-grid engine is now legacy. The cron is paused until at least one real on-chain harness produces a measured delta. See `SYSTEM_AUDIT_2026-06-18.md`.

---

## 0. Why this version exists

After v4.2.0 shipped with `submit_ready=0` for the entire HIPIF chain history (12 saturated slugs, 54k+ findings, every one a catalogue rediscovery or triage probe with no measured delta), the deterministic chain was paused for a substrate change. The audit (`SYSTEM_AUDIT_2026-06-18.md`) diagnosed eight structural defects upstream of the gates; gating, trust boundary, lab notebook, RSI, and skill lockdown remain correct.

v5 introduces a **NativeHarness** substrate:

- Same Python authority gates.
- Same `metadata.trusted=false` discipline.
- Same agent/lab-notebook/RSI loop.
- Different discovery substrate: each in-scope target gets an ABI/IDL-bound harness, a Foundry-harness test that calls live deployed contracts, and a measured-impact oracle.

The synthetic `parameter_spaces.py` + `ContractState` engine moves to `legacy/synthetic/`, retained for fixture-based regression tests but no longer driving the cron.

---

## 1. Executive Summary

v5 is a pivot from "more synthetic trials through cleaner gates" to "build real on-chain harnesses, prove one real measured delta, scale."

The system is currently strongest at:

- rejecting weak or synthetic findings,
- attacking its own candidate assumptions before fork/validator spend,
- mining historical Solodit findings for target and pattern analogues,
- preserving provenance,
- replaying known exploit classes,
- exporting only human-gated submittable artifacts,
- running deterministic HIPIF depth passes through final gate.

The system is currently weakest at:

- ranking concrete candidates by exploitability against deployed state,
- generating value-moving transaction or call sequences,
- running property tests that exercise real target implementations beyond fixture/generator baselines,
- using failed traces to guide the next attempt,
- proving novel economic impact beyond catalogue or triage surfaces.

v4.2 keeps the v4 pivot from "more trials" to "semantic discovery", keeps the v4.1 pre-validation conviction layer, and adds a Solodit corpus layer for historical analogue mining. The goal is to turn real repository code, ABIs, IDLs, storage/account layouts, call graphs, invariants, run traces, bounty scope, and external finding patterns into executable candidates that can reach grade 4 without relying on catalogue analogues.

---

## 2. Non-Negotiable Trust Boundary

These rules remain unchanged from v3.x:

1. LLM, agent, and delegate output is untrusted by default.
2. `validate_hypothesis()` or its v4 schema successor must gate all external proposals.
3. Python validation, evidence grading, credible harness checks, task verifier, and `qualifies_for_submission()` remain authoritative.
4. No autonomous external submission.
5. `submission_alert.json` remains a local human gate only.
6. Catalogue replay, triage-only forks, fixtures, and fee-only CPI deltas must never become `submit_ready`.
7. Every run must leave reproducible artifacts and a lab notebook entry.
8. Solodit findings are historical analogue intelligence only; they never satisfy evidence, reproduction, deployed viability, or submission gates.

---

## 3. Current Shipped Baseline

| Area | Current State |
|------|---------------|
| Tests | 537 passed, 6 skipped in full local run; focused Solodit/self-interrogation/pipeline tests 66 passed; focused KLend harness tests 28 passed; focused Wormhole RSI/economic tests 42 passed; live Wormhole Foundry value probe 2 passed, 3 optional route replays skipped by default; AuditVault corpus integration suite passed; first v5 NativeHarness (Uniswap v4 PoolManager + IHooks) 13 passed + 17 measured-oracle tests + 27 new v5 picker/saturation/label-split tests; pure-Python Keccak-256 helper 6 passed; first v5 measured delta (audit C2) Foundry v4 fork probe 1 passed (PoolManager.initialize slot0 diff recorded at sqrtPriceX96: 0 -> 79,228,162,514,264,337,593,543,950,336); audit corrections C3/C4/C5/C7 wired in `bounty/native_picker.py` + `orchestration/bounty_loop.py`; C6 ABI/IDL bind in `validation/fork_validation.py` + cron full-registry flip + Morpho Blue harness (Phase 3 row 1) 31 new tests |
| Platform intel | 208 Immunefi + 52 Cantina live listings via `platform sync`; Cyfrin Solodit corpus via `platform solodit-sync`; Auditware AuditVault advisory corpus via `platform auditvault-sync` (2383 findings, 826 protocols slug×id pairs across 533 protocols) |
| Export tracks | `bounty/research/` vs `bounty/submittable/` |
| Primary cron | `nightsoul` `nss-hipif-chain` daily 04:00, no-agent deterministic full runner |
| Main targets | Wormhole, Kamino KLend, current Cantina slates, Ethena, Jito |
| Current Cantina slates | uniswap, reserve-protocol, euler, polymarket, coinbase, morpho, pendle, okx, paxos |
| Reproduction | EVM Foundry fork, Solana fixture/validator, KLend harness |
| Self-interrogation | Deterministic conviction reports before CPCV/MC/fork/Solana validation; bounty-depth rank pressure enabled |
| Solodit | Deterministic findings sync, pattern JSONL, metadata enrichment, and authenticated untrusted proposal lane |
| AuditVault | Deterministic finding + pattern + summary sync from Auditware `AuditVault/repo` (gitignored clone); advisory analogue intelligence only; skill `auditvault-research` enables LLM agent offline research without IPC |
| Agent proposal lane | Optional authenticated xAI-OAuth (`grok-4.3`) `hermes chat` turn on `nightsoul` writes untrusted target-pinned proposals into `data/security_results/hermes_proposals/auditvault-*.json`; `metadata.trusted=false`, lineage stamped from AuditVault pattern rows, must still pass `validate_hypothesis()` before integration |
| Submit-ready count | 0, expected because gates block non-credible evidence |

Recent observed run behavior:

- Latest full v4.1 HIPIF run reached 13/13 folds in 4805s with `gate_ok=true` and `submit_ready=false`.
- Latest full v4.2 HIPIF bounty-depth run (2026-06-17, no-agent deterministic) reached 13/13 folds in 3564s with `gate_ok=true` and `submit_ready=false`. Fold summary: scan_all, depth_wormhole (13 findings, 2 fork_repro), kamino_preflight (validator ready), depth_kamino (39 findings, 108 solana_repro), cantina_slates (9 programs x 3 trials), hunt_rotation, rsi_fold, depth_wormhole_bridge (13 findings, 10 fork_repro), refine_conditional, coordinator_conditional, journal_fold, gate.
- Wormhole and bridge passes repeatedly produced many fork repros, but triage/catalogue style only.
- KLend produced many `solana_reproduced` records, but fee-only CPI remained blocked.
- Cantina slates produced fork repros, often via analogue harnesses.
- Findings were recorded and RSI generated refinement queue entries, scan boosts, cooldowns, and config fallbacks.
- Solodit sync skips cleanly without `CYFRIN_API_KEY`; when present, `scan_all` writes corpus and pattern artifacts before target depth.
- KLend oracle borrow probing now reaches source-derived account setup on a cloned executable Farms/KLend/KVault/oracle validator profile. User metadata, vanilla obligation, USDC ATA setup, reserve refresh, and obligation refresh confirm on-chain; the borrow attempt remains non-submittable with zero protocol delta and currently fails because cloned Scope USDC price/TWAP are too old, leaving borrow reserve price status insufficient for borrow checks.
- Wormhole triage-surface/no-delta fork traces are classified as `missing_economic_impact` and routed to `generate_value_moving_poc`; fork evidence stamps `economic_impact_verified=false` when triage evidence lacks token/native delta, bridge accounting violation, or bounded TVS-at-risk proof. A live USDC token-bridge value probe now asserts malformed `completeTransfer` leaves bridge balance and `outstandingBridged(USDC)` unchanged, a mocked-authorized baseline proves deployed accounting moves exactly 1 USDC only when core verification is harnessed, and Wormholescan real signed VAA replay/corpus classification verifies authorized messages without treating legitimate replay as impact.

---

## 4. Root-Cause Audit Findings

### F1. Hypotheses are too abstract

Current parameter spaces sample broad floats and choices such as `oracle_dependency_score`, `role_bypass_severity`, `chain_depth`, and `target_function_preference`. They do not encode concrete functions, accounts, actors, storage slots, program instructions, bridge messages, signer constraints, token accounts, call sequences, or expected balance deltas.

**Impact:** Search spends compute on generic ideas that cannot become executable PoCs without substantial manual translation.

**Required fix:** Introduce concrete, target-bound candidate schemas.

### F2. File triage is keyword/path based

`triage/file_ranker.py` ranks files by regex matches in paths. This is useful for cheap scanning but insufficient for vulnerability discovery.

**Impact:** The system knows that a file says "oracle" or "bridge" but not which functions read an oracle, who can call them, whether stale reads influence borrow limits, or where value moves.

**Required fix:** Add AST, ABI, IDL, call graph, and data-flow extraction.

### F3. PBT does not execute target code

`invariants/pbt.py` checks synthetic `state_hints` and toy formulas. It does not run Foundry invariant tests, Solana program tests, or target-specific state transitions.

**Impact:** Property-based testing currently creates ranking signals, not bugs.

**Required fix:** Generate and run real target-bound invariant tests.

### F4. Fork validation replays fixed harnesses

Fork validation picks catalogue anchors, top-N candidates, or template fallbacks, then runs predetermined Foundry tests. Candidate parameters are mostly environment inputs to fixed tests.

**Impact:** The system verifies known harness predicates more often than it verifies candidate-specific exploits.

**Required fix:** Generate per-candidate PoC tests and assertions.

### F5. KLend probes are hardcoded and not IDL/account-layout driven

KLend live probes have hardcoded pseudo instruction prefixes and narrative impact values. Live mode measures deltas, but the transaction surface is not yet derived from real instructions and account layouts.

**Impact:** The harness can prove deployment and fee-only execution, but not a protocol-level exploit path.

**Required fix:** Decode real instruction discriminators, required accounts, reserve/vault layouts, and token deltas.

### F6. Wormhole triage does not become economic impact

Wormhole live forks verify governance/bridge/pauser surfaces, but triage-surface evidence is intentionally exported only as research.

**Impact:** High-grade research packs are not submittable because they do not demonstrate novel economic impact.

**Required fix:** Build target-specific economic assertions: unauthorized message acceptance, guardian/quorum bypass impact, pause authority misuse impact, bridge transfer ledger imbalance, or token movement.

### F7. Target pinning is incomplete

Delegate proposals can be generated for Wormhole while the bounty loop picks another target from the global queue.

**Impact:** Expensive reasoning does not reliably execute against the intended target.

**Required fix:** Proposal files must carry enforced `target_slug`, `campaign_id`, and compatible config path.

**Status:** Fixed in v4.0.0 through proposal metadata and `bounty loop --target` fail-fast checks.

### F8. Agent cron could false-pass

Agent-mode cron may stop after a short bootstrap response and still be recorded as OK.

**Impact:** Night Shift can silently skip the actual chain.

**Required fix:** Cron success must require expected folds, gate phase completion, and lab notebook write.

**Status:** Fixed operationally by making the primary 04:00 `nightsoul` job no-agent deterministic. Agent/hybrid remains available for manual work only.

---

## 5. v4.0 Target Architecture

v4.0 adds a semantic discovery layer before the existing validation layer.

```text
Platform Intel
  -> Scope Resolver
  -> Source Sync
  -> Semantic Recon
  -> Candidate Builder
  -> Solodit Corpus Enrichment
  -> Invariant/PoC Synthesizer
  -> Self-Interrogation Gate
  -> Dynamic Verification
  -> Failure Trace RSI
  -> Existing Evidence Gates
  -> Research/Submittable Export
```

### New layers

| Layer | Name | Purpose |
|-------|------|---------|
| 0.5 | Source + Scope Resolver | Bind bounty scope to repos, contracts, programs, ABIs, IDLs, deployments |
| 1.5 | Semantic Recon | Extract functions, instructions, roles, accounts, storage, value flows, call graphs |
| 2.5 | Concrete Candidate Builder | Convert semantic facts into executable hypotheses |
| 3.2 | Solodit Corpus Enrichment | Sync historical findings and stamp analogue metadata before conviction review |
| 3.6 | PoC + Invariant Synthesis | Generate target-specific Foundry/Solana tests |
| 4.1 | Self-Interrogation Gate | Challenge assumptions, missing bindings, replay risk, and impact before expensive validation |
| 4.5 | Failure Trace RSI | Learn from reverts, account diffs, coverage, and failed assumptions |
| 6.7 | External Tool Ingestion | Opengrep, Trail of Bits workflows, BBOT/SpiderFoot, Strix/Caido where relevant |

---

## 6. Concrete Candidate Schema

The v4 candidate format should coexist with current `AttackVector` until migration is complete.

```json
{
  "candidate_id": "uuid",
  "target_slug": "wormhole",
  "campaign_id": "wormhole-bridge-2026q2",
  "chain": "ethereum|solana|base|polygon|...",
  "source_ref": {
    "repo": "sources/wormhole/repo",
    "commit": "git sha",
    "file": "contracts/...",
    "symbol": "function or instruction"
  },
  "entrypoint": {
    "kind": "solidity_function|solana_instruction|http_endpoint|keeper_job",
    "name": "completeTransfer",
    "selector_or_discriminator": "0x..."
  },
  "actors": [
    {"role": "attacker", "constraints": ["not_owner", "funded"]},
    {"role": "guardian", "constraints": ["absent_or_spoofed"]}
  ],
  "state_bindings": {
    "contracts": {},
    "accounts": {},
    "storage_slots": {},
    "token_accounts": {}
  },
  "sequence": [
    {"call": "step name", "params": {}, "sender": "attacker"}
  ],
  "invariant": {
    "id": "bridge_conservation",
    "predicate": "post_total_assets >= pre_total_assets",
    "expected_violation": "attacker_balance_increases_without_authorized_burn_or_lock"
  },
  "impact_oracle": {
    "metric": "DELTA_WEI|DELTA_LAMPORTS|TOKEN_DELTA|TVS_AT_RISK",
    "threshold": "configured threshold"
  },
  "provenance": {
    "source": "semantic_recon|opengrep|llm_delegate|manual",
    "trusted": false,
    "evidence": []
  }
}
```

Acceptance:

- Every generated candidate must be target-pinned.
- Every candidate must name an entrypoint and invariant.
- No candidate can reach grade 3+ without an executable verifier.

---

## 6.5 Workstream A0 - Adversarial Self-Interrogation

### Objective

Reduce wasted validation spend and repeated weak hypotheses by forcing each high-ranked candidate to survive a deterministic skeptical pass before CPCV, Monte Carlo, Foundry fork, or Solana validator lanes consume budget.

### Module

| Module | Path | Purpose |
|--------|------|---------|
| Self-interrogation gate | `src/night_shift_security/validation/self_interrogation.py` | Build `ConvictionReport` metadata from deterministic challenges and surviving arguments |

### Conviction report

Each analyzed candidate receives metadata:

```json
{
  "self_interrogation": {
    "candidate_label": "label",
    "conviction_score": 0.0,
    "recommended_action": "proceed|revise|discard|escalate",
    "adversarial_challenges": [],
    "surviving_arguments": [],
    "risks": [],
    "open_assumptions": [],
    "lineage_refs": []
  }
}
```

The gate attacks the candidate on:

- existing deterministic rejection state,
- missing economic impact or invariant,
- missing target/source/entrypoint binding,
- catalogue-only or replay-only risk,
- overfitting signals from CPCV/PBO when available,
- missing reproduction evidence during promotion-stage review.

### Operating modes

| Mode | Behavior |
|------|----------|
| `advisory` | Default. Stamp reports and leave existing gates authoritative. |
| `filter` | Reject low-conviction non-catalogue candidates before expensive validation. |
| `rank_adjustment` | Small severity-score pressure so high-conviction candidates reach top-N validation lanes first. Enabled automatically for HIPIF bounty-depth configs. |

### Trust boundary

- Conviction reports are advisory evidence, not proof.
- They never satisfy evidence-grade, task-verifier, credible-harness, or submission gates.
- Catalogue seeds and ground-truth anchors bypass hard filtering so rediscovery tests remain stable.
- Every report is stored in vector metadata and can flow into findings-store lineage.

### Acceptance

- Pipeline logs self-interrogation stats before CPCV/MC/fork/Solana lanes.
- Default config enables advisory reports without changing pass/fail behavior.
- Bounty-depth config enables rank pressure but not hard filtering.
- Unit tests cover proceed/revise/discard paths, metadata stamping, filter mode, and rank adjustment.

---

## 6.6 Workstream A1 - Solodit Corpus Enrichment

### Objective

Use Cyfrin Solodit as a historical vulnerability corpus that improves candidate prioritization and proposal generation without weakening deterministic NSS gates.

### Modules

| Module | Path | Purpose |
|--------|------|---------|
| Solodit sync | `src/night_shift_security/platform/solodit.py` | Fetch, normalize, and distill Solodit findings |
| Solodit skill | `hermes/skills/solodit-research/SKILL.md` | Authenticated agent workflow for untrusted next-run proposals |

### Deterministic sync

`platform solodit-sync` calls the Solodit Findings API with `CYFRIN_API_KEY` and writes `data/security_results/platform/solodit_findings.json`. `platform solodit-patterns` distills the synced corpus into `data/security_results/knowledge/solodit_patterns.jsonl`.

Default scope is `target-plus-pattern`: current NSS target/protocol names plus high-signal vulnerability tags such as Oracle, Access Control, Bridge, Reentrancy, Flash Loan, Price Manipulation, and Logic Error. Missing `CYFRIN_API_KEY` is a clean skip, not a cron failure.

### Pipeline use

The pipeline stamps matching candidates with Solodit metadata before self-interrogation:

- `solodit_refs`
- `solodit_tags`
- `solodit_quality_max`
- `solodit_rarity_max`

These fields may influence triage and conviction context only. They cannot satisfy evidence grade, credible harness, task verifier, deployed viability, or submission criteria.

### Hybrid agent lane

The optional `nss-solodit-agent-proposals` cron runs after the deterministic HIPIF chain and uses `solodit-research` to write untrusted target-pinned proposal JSON for the next deterministic run. The agent lane must not post externally or mark findings submit-ready.

### Acceptance

- Unit tests cover query presets, normalization, no-key skip, pattern extraction, and candidate metadata enrichment.
- HIPIF `scan_all` includes Solodit sync status and pattern count.
- Proposal outputs remain subject to `validate_hypothesis()` and target/config fail-fast checks.

---

## 6.7 Workstream A2 - AuditVault Advisory Corpus Ingestion

### Objective

Use the Auditware `AuditVault` open dataset as a second historical vulnerability corpus, alongside Cyfrin Solodit, to broaden pattern coverage for the deterministic sync layer and to enable a tightly-scoped LLM agent research turn that writes `metadata.trusted=false` proposals without ever influencing pipeline gates.

### Modules

| Module | Path | Purpose |
|--------|------|---------|
| AuditVault sync | `src/night_shift_security/platform/auditvault.py` | Fetch, normalize, and distill AuditVault findings, protocols, and id.slug pairs from a gitignored local clone |
| AuditVault skill | `hermes/skills/auditvault-research/SKILL.md` | Authenticated agent workflow for untrusted AuditVault-derived next-run proposals |

### Deterministic sync

The pipeline clones `https://github.com/Auditware/AuditVault.git` into the gitignored `sources/auditvault/repo/` (the LICENSE links this codebase under MIT and credits Auditware as the author). Three deterministic commands then materialize artefacts under `data/security_results/`:

- `platform auditvault-sync` -> `data/security_results/platform/auditvault_findings.json` (status, finding_count, protocol_count, slug_pairs).
- `platform auditvault-patterns` -> two JSONL stores: `data/security_results/knowledge/auditvault_patterns.jsonl` (one row per finding with axis/title/severity/protocol) and `data/security_results/knowledge/auditvault_ids.jsonl` (one row per `(slug, id)` pair).
- `platform auditvault-summary` -> aggregated bucket-by-axis report for downstream `auditvault-research` context.

HIPIF `scan_all` invokes sync best-effort; absence of the local clone fails the single subcommand without breaking the deterministic chain.

### Pipeline semantics

- AuditVault data joins the same authoritative Python gates as every other corpus (Solodit, Immunefi, Cantina, Hypothesize-This). It cannot satisfy evidence grade, task verifier, credible harness, deployed viability, or submission criteria.
- AuditVault pattern rows provide cross-corpus analogue confirmation only when `auditvault-ref-unique-pattern-id` exists; lineage stamping will never raise an analogue flag that should not exist.
- The non-negotiable trust boundary treats AuditVault just like LLM output: any proposal derived from it must carry `metadata.trusted=false`, and the deterministic runner alone executes the chain.

### Acceptance

- Unit tests cover sync, pattern extraction, id extraction, summary, no-key skip, gitignore behavior, and corpus enrichment.
- HIPIF `scan_all` reports AuditVault status (`ok` or `skipped`) and totals.
- AuditVault-derived agent proposals are scoped to `wormhole` and similar high-priority targets, never global targets.

## 6.8 Workstream A3 - Agent Proposal Lane (Optional Authenticated xAI-OAuth)

### Objective

Add a strictly-scoped LLM agent turn that runs offline against the deterministic artefacts (`auditvault_findings`, `auditvault_patterns`, `folded_context`, `loop/state`, `data/security_results/platform/intel`) and writes one untrusted `auditvault-*.json` proposal per run. The agent must never execute the chain and must never touch pipeline Python.

### Operating envelope

- Profile: `nightsoul` (overlayed on `night-shift` plus NSS v4 skills), skills restricted to the 20 NSS-v4 skill symlinks (see §6.9) plus the new `auditvault-research` skill.
- Provider: `xai-oauth` (login flow managed by Hermes OAuth helper, persisted in `~/.hermes/profiles/nightsoul/memories/auth.json`).
- Model: `grok-4.3` (xai-oauth default).
- Invocation: `hermes chat -q "<task>" -s auditvault-research -s solodit-research --profile nightsoul --max-turns 25`.
- Output: `data/security_results/hermes_proposals/auditvault-<YYYYMMDD>.json`, plus a `latest.json` symlink re-pointing to the most recent proposal. A lab notebook entry summarizing the agent turn must be written by the agent under `data/security_results/lab_notebook/auditvault-agent-*.md`.

### Hard guarantees

1. Agent output carries `metadata.trusted=false` and `force_target=true`. Targets are restricted to the NSS target universe (Wormhole, KLend, Cantina slates).
2. `severity_score=0.0` is set by default; the deterministic runner alone may assign severity.
3. `auditvault-ref-unique-pattern-id` is the canonical AuditVault lineage stamp; lineage must reference at least one AuditVault pattern row.
4. Agent never publishes externally; it writes `submission_alert.json`, posts to bounties, or mutates core pipeline Python.
5. Submission gates (`qualifies_for_submission()`) ignore `auditvault-*` proposals unless the proposal also passes `validate_hypothesis()` and clears all default gates; recall that `validated_recently_horizon=72h` and proposals older than that revert to `untrusted`.

### Acceptance

- Agent proposal scenarios covered by unit tests (auditvault-derived, force_target, lineage stamp, severity=0.0 default, max-turns guard).
- A nightly 07:00 cron recipe is added to `hermes/cron/jobs.example.yaml` purely as documentation; production default does not enable the recipe.

## 6.9 Workstream A4 - Hermes `nightsoul` Skill Profile Lockdown

### Objective

Prevent IRL skills (smart-home, browser-harness, manim-composer, GSAP, ...) from polluting the `nightsoul` profile so the LLM agent only sees the NSS-v4 skill surface and the new `auditvault-research` skill.

### Enforced profile

`~/.hermes/profiles/nightsoul/skills/` contains exactly 20 symlinks:

| Skill | Type |
|-------|------|
| `hipif` | NSS v4 |
| `bounty-loop` | NSS v4 |
| `recursive-improvement` | NSS v4 |
| `coordinator-cycle` | NSS v4 |
| `lab-notebook` | NSS v4 |
| `hypothesis-expansion` | NSS v4 |
| `immunefi-scan` | NSS v4 |
| `investigate-from-scan` | NSS v4 |
| `novel-vector-digest` | NSS v4 |
| `knowledge-campaign` | NSS v4 |
| `operator-checkpoint` | NSS v4 |
| `operator-submit` | NSS v4 |
| `operator-exploit` | NSS v4 |
| `operator-recon` | NSS v4 |
| `operator-triage` | NSS v4 |
| `solodit-research` | NSS v4 |
| `shoestring-pack` | NSS v4 |
| `day-shift-cycle` | NSS v4 |
| `night-shift-run` | NSS v4 |
| `auditvault-research` | New (audited alongside Solodit) |

### Acceptance

- A unit test enumerates the skill directory, asserts exactly those 20 symlinks exist, and asserts no legacy skill directories leak back into the profile.
- Re-installation via `./hermes/install-nightsoul-overlay.sh` ends with exactly those 20 skills.

### Objective

Replace keyword-only triage with code-aware recon for Solidity, Rust/Solana, TypeScript/JavaScript, Python, Go, and protocol config.

### Modules

| Module | Path | Purpose |
|--------|------|---------|
| Solidity parser | `src/night_shift_security/semantic/solidity.py` | ABI, AST, modifiers, events, external calls, storage writes |
| Solana parser | `src/night_shift_security/semantic/solana.py` | IDL, Anchor accounts, discriminators, signer/writable constraints |
| Generic code map | `src/night_shift_security/semantic/code_map.py` | Language-agnostic symbols and edges |
| Value flow | `src/night_shift_security/semantic/value_flow.py` | Token/native balance movement sources and sinks |
| Authority graph | `src/night_shift_security/semantic/authority.py` | owners, admins, guardians, pausers, upgrade authorities |
| Oracle graph | `src/night_shift_security/semantic/oracles.py` | reads, freshness checks, consumers, manipulation paths |
| Bridge graph | `src/night_shift_security/semantic/bridges.py` | message verification, replay protection, mint/burn/lock/release |

### Outputs

```text
data/security_results/semantic/{slug}/code_map.json
data/security_results/semantic/{slug}/entrypoints.json
data/security_results/semantic/{slug}/authority_graph.json
data/security_results/semantic/{slug}/value_flows.json
data/security_results/semantic/{slug}/candidate_seeds.jsonl
```

### CLI

```bash
.venv/bin/python -m night_shift_security.cli.main semantic map \
  --slug wormhole \
  --repo sources/wormhole/repo \
  --out data/security_results/semantic/wormhole

.venv/bin/python -m night_shift_security.cli.main semantic candidates \
  --slug wormhole \
  --kind bridge
```

### Acceptance

- For Solidity targets: list external/public functions, modifiers, state writes, token transfers, delegatecalls, upgrade paths, oracle reads, and bridge-message flows.
- For Anchor/Solana targets: list instructions, discriminators, account metas, signer/writable constraints, owner constraints, token account roles, and CPI edges.
- Recon artifacts must include source commit and parser version.

---

## 8. Workstream B - Opengrep/Semantic Rule Ingestion

### Objective

Use Opengrep or Semgrep-compatible rules to generate high-signal, target-bound candidate seeds.

### External tool

- Primary: https://github.com/opengrep/opengrep
- Rule compatibility: Semgrep-style YAML rules.

### Rule families

| Family | Examples |
|--------|----------|
| Access control | missing modifier, owner/admin mismatch, unchecked pauser/guardian, signer confusion |
| Bridge safety | missing replay check, unchecked message emitter, quorum mismatch, chain ID confusion |
| Oracle safety | stale read, missing confidence interval, wrong decimals, pre-update borrow path |
| Token/account safety | unchecked token program, wrong vault authority, missing mint check |
| Upgradeability | uninitialized proxy, unsafe delegatecall, storage collision, mutable implementation |
| Arithmetic/accounting | rounding value leak, fee bypass, supply/asset mismatch |
| Solana CPI | arbitrary CPI target, writable account confusion, PDA seed mismatch |

### Outputs

```text
rules/nss/{family}.yaml
data/security_results/semantic/{slug}/opengrep.sarif
data/security_results/semantic/{slug}/opengrep_candidates.jsonl
```

### Integration

Opengrep findings must be normalized into concrete candidates:

```text
SARIF finding
  -> source location
  -> semantic code map join
  -> target entrypoint
  -> invariant template
  -> v4 candidate
```

### Acceptance

- A finding without source location, entrypoint, and invariant is triage-only.
- Rules must have fixture tests in `tests/fixtures/opengrep_rules/`.
- Opengrep output must never bypass Python validation.

---

## 9. Workstream C - Real Property-Based Testing

### Objective

Move from synthetic `state_hints` to executable invariants over target code.

### EVM

Generate Foundry invariant tests and fuzz tests:

```text
foundry/generated/{slug}/{candidate_id}.t.sol
```

Required properties:

- balance conservation,
- no unauthorized role transition,
- no mint/release without corresponding burn/lock/message,
- borrow cannot exceed collateral under oracle constraints,
- liquidation cannot leave protocol under-reserved,
- upgrade cannot change implementation without authorized path.

### Solana

Generate local validator or LiteSVM/Mollusk-style instruction tests where feasible:

```text
solana/generated/{slug}/{candidate_id}_test.py
solana/generated/{slug}/{candidate_id}_accounts.json
```

Required properties:

- signer and writable constraints hold,
- token vault deltas match expected accounting,
- CPI targets are constrained,
- reserve/account ownership is verified,
- stale oracle state cannot alter borrow/liquidation outcomes.

### Acceptance

- Generated tests must run in CI when fixture-only.
- Live validator tests may be skipped without RPC, but must run in bounty-depth mode.
- Counterexamples must be stored as refinement seeds.

---

## 10. Workstream D - Candidate-Specific PoC Synthesis

### Objective

Each promising candidate should get a generated executable PoC, not just a generic harness run.

### EVM PoC requirements

Each generated Foundry test must:

1. Fork at a deterministic block.
2. Bind real deployed contracts.
3. Set actor balances/approvals explicitly.
4. Execute the candidate sequence.
5. Emit `DELTA_WEI`, `TOKEN_DELTA`, or `TVS_AT_RISK`.
6. Fail closed when target state cannot be bound.

### Solana PoC requirements

Each generated validator test must:

1. Clone required programs and accounts.
2. Build a real instruction with real discriminator.
3. Use decoded account metas.
4. Track wallet and protocol vault deltas.
5. Emit `MEASURED_DELTA_LAMPORTS`, token deltas, and invariant ID.
6. Distinguish failed-on-chain from successful exploit.

### Acceptance

- Generic template fallback cannot produce `submit_ready`.
- A candidate-specific PoC must be linked in `finding.reproduction_steps`.
- Generated PoCs must be reproducible from exported artifacts.

---

## 11. Workstream E - KLend Live Harness v2

### Objective

Turn KLend from fee-only CPI probing into real instruction-level exploit testing.

### Required improvements

1. Import or derive real KLend IDL/instruction discriminators.
2. Decode `sources/kamino/klend_accounts.json` into typed roles.
3. Build real borrow, deposit, withdraw, liquidate, refresh reserve, and oracle-update paths where public instructions allow.
4. Track USDC/SOL vault token deltas, obligation state, reserve liquidity, and attacker balances.
5. Add account-diff snapshots before and after each probe.
6. Add live failure classifiers: missing account, bad discriminator, owner mismatch, custom program error, no protocol delta, fee-only.

### New artifacts

```text
data/security_results/klend/instruction_map.json
data/security_results/klend/account_roles.json
data/security_results/klend/probe_results.jsonl
data/security_results/klend/account_diffs/{run_id}.json
```

### Acceptance

- `HARNESS_MODE:live_executed` must require a real instruction and non-fee protocol or attacker delta.
- Fee-only CPI remains blocked.
- `MEASURED_DELTA_LAMPORTS:0` remains blocked.
- A KLend candidate can reach grade 4 only with root cause, account diff, and replay script.

---

## 12. Workstream F - Wormhole Economic Impact

### Objective

Move Wormhole from triage-surface verification to economic-impact proof.

### Candidate families

| Family | Required invariant |
|--------|--------------------|
| Message replay | Same message cannot release/mint twice |
| Guardian/quorum | Unauthorized quorum cannot authorize value movement |
| Chain/emitter confusion | Wrong emitter/chain cannot authorize release |
| Pause authority | Unauthorized pause/unpause cannot block or unlock economic action |
| Upgrade/governance | Unauthorized governance action cannot alter critical state |
| Bridge accounting | Released assets must correspond to locked/burned source assets |

### Required outputs

```text
foundry/generated/wormhole/{candidate_id}.t.sol
data/security_results/wormhole/message_fixtures/{candidate_id}.json
data/security_results/wormhole/economic_deltas.jsonl
```

### Acceptance

- `TRIAGE_SURFACE_VERIFIED:1` is research only.
- Wormhole grade 4 requires token/native delta, bridge accounting violation, or bounded TVS-at-risk with source-level root cause.

---

## 13. Workstream G - Target-Pinned Proposal Execution

### Objective

Ensure generated proposals execute against the intended target and config.

### Proposal schema additions

```json
{
  "target_slug": "wormhole",
  "campaign_id": "wormhole-bridge-2026q2",
  "required_config": "src/night_shift_security/config/wormhole_shoestring.json",
  "allowed_templates": ["access_control_escalation", "composability_risk"],
  "source_artifacts": [
    "data/security_results/triage/wormhole_files.json"
  ],
  "force_target": true
}
```

### CLI behavior

If `force_target=true`, `bounty loop` must not pick from the global queue.

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/wormhole.json \
  bounty loop --target wormhole --iterations 1
```

### Acceptance

- A Wormhole proposal cannot run against Beanstalk.
- Run reports must include `proposal_target_match: true|false`.
- Mismatches fail the run before validation.

---

## 14. Workstream H - Failure Trace RSI

### Objective

Use failed executions as useful search information.

### Inputs

- EVM revert reason,
- custom error selector,
- Foundry traces,
- changed storage slots,
- gas/coverage profile,
- Solana program logs,
- custom program error,
- account owner/mutability/signature mismatch,
- pre/post account diffs,
- candidate invariant outcome.

### New artifacts

```text
data/security_results/traces/{slug}/{candidate_id}.json
data/security_results/knowledge/failure_signatures.jsonl
data/security_results/loop/refinement_hints.json
```

### RSI actions

| Failure | Next Action |
|---------|-------------|
| Missing signer | mutate actor/account role |
| Wrong account owner | repair account binding |
| Bad discriminator | refresh IDL/instruction map |
| Revert before value movement | mutate prestate or call order |
| No delta after success | downgrade to triage or add impact oracle |
| Wormhole triage surface with no measured delta | generate value-moving PoC |
| Catalogue-only replay | demand semantic seed or new target |
| Repeated fingerprint | stop trials, not cooldown only |

### Acceptance

- Repeated top findings should stop depth trials and queue a semantic recon task.
- RSI must distinguish "bad idea" from "bad harness binding."

---

## 15. Workstream I - Cron Hardening

### Objective

Prevent false OK runs.

### Success criteria for `nss-hipif-chain`

The production cron job must run `nss-hipif-chain.sh` in no-agent deterministic mode. Success is valid only if:

1. `scan_all` fold exists.
2. At least one depth fold exists.
3. Gate fold exists.
4. `chain_status=complete`.
5. Lab notebook entry was written.
6. `submission_alert.json` state was checked.

### Current behavior

- `NSS_HIPIF_MODE` defaults to `deterministic`.
- The installed `nightsoul` job is `no-agent`, has no skills attached, and runs `nss-hipif-chain.sh` directly.
- The script exits only after `nss-hipif-chain-run.py --phase full` exits.

### Acceptance

- Bootstrap-only output cannot mark the primary cron successful.
- Cron output includes fold count and gate status.

---

## 16. Workstream J - External Tool Expansion

### Anthropic Defending Code Reference Harness

Reference: https://github.com/anthropics/defending-code-reference-harness

Use as the model for:

- sandboxed autonomous vulnerability pipeline,
- recon -> find -> verify -> report -> patch loop,
- candidate verification discipline,
- agent sandboxing and egress limits,
- customization docs for stack-specific harnesses.

Do not import as a black box. Adapt the workflow shape to DeFi targets.

### Opengrep

Reference: https://github.com/opengrep/opengrep

Use for:

- semantic static rules,
- SARIF ingestion,
- taint-style source/sink mapping,
- custom Solidity/Rust/TypeScript rules.

### Trail of Bits Skills

Reference: https://github.com/trailofbits/skills

High-priority ideas:

- `entry-point-analyzer`,
- `building-secure-contracts`,
- `property-based-testing`,
- `spec-to-code-compliance`,
- `variant-analysis`,
- `semgrep-rule-creator`,
- `fp-check`,
- `static-analysis`.

Use these as workflow references or optional installed skills, not as trusted validators.

### BBOT and SpiderFoot

References:

- https://github.com/blacklanternsecurity/bbot
- https://github.com/smicallef/spiderfoot

Use for:

- bounty programs with web, API, cloud, or domain scope,
- subdomain/API discovery,
- exposed service mapping,
- platform intel enrichment.

Do not use for core protocol internals unless scope includes off-chain systems.

### Strix and Caido Skills

References:

- https://github.com/usestrix/strix
- https://github.com/caido/skills

Use for:

- web/API targets,
- business logic and IDOR-style bounty scopes,
- off-chain dashboards, relayers, or API services.

Lower priority for pure EVM/Solana protocol internals.

---

## 17. Evidence Grades v4

Existing grade definitions remain but receive stricter source requirements.

| Grade | Meaning | v4 Requirement |
|-------|---------|----------------|
| 0 | None | Rejected or no useful evidence |
| 1 | Structural survivor | Valid candidate with target-bound entrypoint and invariant |
| 2 | Statistical/semantic survivor | CPCV/PBO or semantic rule + feasible state binding |
| 3 | Reproduced | Candidate-specific fork/validator/property test executed |
| 4 | Root cause + impact | Source root cause, replayable PoC, measured delta or bounded TVS |

Caps:

- No source-bound entrypoint: max grade 1.
- No executable verifier: max grade 2.
- Generic harness replay: max grade 3 for research, never submittable.
- Triage surface without economic impact: research only.
- Fee-only CPI: max grade 2.

---

## 18. Submit-Ready Gate v4

`qualifies_for_submission()` must require all current gates plus:

1. `candidate_schema_version >= 4`.
2. `target_pinned == true`.
3. `source_ref.commit` present.
4. `entrypoint.selector_or_discriminator` present when applicable.
5. Candidate-specific reproduction artifact exists.
6. `impact_oracle.metric` is measured, not inferred.
7. Failure trace is absent or classified non-blocking.
8. Research export was reviewed by `operator-submit` or equivalent human gate.

---

## 19. Data Model Additions

### New directories

```text
src/night_shift_security/semantic/
src/night_shift_security/pocgen/
src/night_shift_security/tools/
rules/nss/
foundry/generated/
solana/generated/
data/security_results/semantic/
data/security_results/traces/
data/security_results/klend/
data/security_results/wormhole/
```

### New JSONL stores

```text
data/security_results/knowledge/concrete_candidates.jsonl
data/security_results/knowledge/failure_signatures.jsonl
data/security_results/knowledge/tool_findings.jsonl
```

### Required provenance fields

- `tool_name`
- `tool_version`
- `rule_id`
- `source_commit`
- `generated_at`
- `trusted=false` unless produced by deterministic parser
- `validation_status`

---

## 20. CLI Additions

```bash
# Semantic recon
.venv/bin/python -m night_shift_security.cli.main semantic map --slug wormhole --repo sources/wormhole/repo

# Static rules
.venv/bin/python -m night_shift_security.cli.main tools opengrep --slug wormhole --repo sources/wormhole/repo

# Candidate construction
.venv/bin/python -m night_shift_security.cli.main semantic candidates --slug wormhole --from-opengrep

# PoC generation
.venv/bin/python -m night_shift_security.cli.main poc generate --candidate-id <id>

# Candidate-specific verification
.venv/bin/python -m night_shift_security.cli.main poc verify --candidate-id <id>

# Failure trace summarization
.venv/bin/python -m night_shift_security.cli.main traces summarize --slug wormhole

# Target-pinned bounty loop
.venv/bin/python -m night_shift_security.cli.main --proposals <path> bounty loop --target wormhole --iterations 1
```

---

## 21. Shipped v4 Baseline

v4.0.0 shipped the audit-to-implementation baseline as one integrated release. v4.1.0 adds pre-validation adversarial self-interrogation and bounty-depth conviction rank pressure.

| Area | Status |
|------|--------|
| Target pinning + cron truth | Shipped. Proposal metadata, `bounty loop --target`, no-agent primary cron, fold/gate truth checks. |
| Semantic recon MVP | Shipped. Solidity, Rust/Solana, Anchor IDL, entrypoints, authority/value/oracle/bridge graphs. |
| Opengrep integration | Shipped. Rule directory, wrapper, SARIF parser, fixture coverage, candidate ingestion. |
| Candidate schema/store | Shipped. `ConcreteCandidate`, JSONL store, source/provenance requirements, evidence caps. |
| PoC generation MVP | Shipped. Foundry/Solana fail-closed generation and verifier CLI. |
| KLend harness v2 | Shipped baseline. Discriminator map, typed roles, account diffs, probe store, failure classifiers. |
| Wormhole economic impact | Shipped baseline. Economic invariants, message fixtures, generated fail-closed PoCs, submit gate enforcement. |
| Failure Trace RSI | Shipped. Failure signatures and refinement hints from verifier failures. |
| Self-interrogation gate | Shipped. Deterministic conviction reports before expensive validation; advisory by default, rank pressure in bounty depth. |
| Off-chain wrappers | Shipped baseline. Scoped wrappers for web/API recon tools; execution depends on installed tools and scope. |

Important distinction: shipped baseline means the system can discover, bind, generate, verify, record, and gate these surfaces. It does not mean a bounty-grade bug has been found. The current frontier is candidate quality and measured value movement.

## 21.1 Forward Backlog

### P0 - Value-Moving Reproduction

- Bind top Wormhole concrete candidates to deployed core/token_bridge state.
- Replace KLend fee-only/no-delta probes with real protocol/account/token deltas.
- Promote only candidates with source root cause, executable repro, and measured non-fee impact.

### P1 - Native Target Harnesses

- Add native harnesses for Uniswap, Morpho, Pendle, OKX, Paxos, Reserve, Euler, Coinbase, and Polymarket where analogue configs are still carrying coverage.
- Run real Opengrep/Semgrep binaries in environments where the tools are installed.
- Add a mocked full-chain E2E test for `nss-hipif-chain-run.py --phase full`.

### P2 - New Execution Lanes

- Add a Cosmos SDK/CometBFT lane before scheduling dYdX in default nightly slates.
- Expand scoped off-chain testing for web/API/relayer bounty surfaces with BBOT, SpiderFoot, Strix, and Caido when target scope allows it.

---

## 22. Testing Strategy

### Unit tests

- Self-interrogation conviction reports, metadata stamping, filter mode, and rank adjustment.
- Semantic parsers on fixture Solidity/Rust/Anchor code.
- Opengrep SARIF normalization.
- Concrete candidate validation.
- Proposal target pinning.
- Evidence grade caps.
- Trace classification.

### Integration tests

- `semantic map` -> candidates -> generated PoC on fixture target.
- Wormhole proposal forced to Wormhole config.
- KLend fixture remains blocked from submit-ready.
- Fee-only live CPI remains blocked.
- Generated Foundry PoC emits delta markers.

### Live optional tests

- Foundry fork tests with `ETHEREUM_RPC_URL`.
- Solana validator tests with `SOLANA_MAINNET_RPC_URL`.
- KLend live probe with account diffs.

### Regression tests

- Catalogue anchors still reproduce.
- `bounty/submittable/` remains empty for catalogue-only and triage-only runs.
- Agent bootstrap-only cron fails health.

---

## 23. Documentation Requirements

When implementing each backlog item:

1. Update this `SPEC.md`.
2. Add `CHANGELOG.md` entry.
3. Update `AUDIT.md` gap status.
4. Update `README.md` status if behavior changes.
5. Add lab notebook entry after live runs.
6. Record gotchas in Hermes skills if an operator workflow changes.

---

## 24. Current Priority Queue

1. **Wormhole deployed-state binding**: turn top concrete candidates into value-moving bridge/core assertions.
2. **KLend non-fee delta**: build a real instruction path that changes protocol or attacker balances beyond transaction fees.
3. **Native Cantina harnesses**: replace analogue-only fork coverage for current high-value slates.
4. **Mocked full-chain E2E**: prevent regressions in the no-agent `--phase full` cron runner.
5. **Real static-tool execution**: run Opengrep/Semgrep where installed and feed SARIF into candidate generation.
6. **dYdX execution lane**: add Cosmos SDK/CometBFT harnessing before default scheduling.
7. **Off-chain recon expansion**: use BBOT/SpiderFoot/Strix/Caido only for scoped web/API/relayer surfaces.

---

## 25. Definition of Done for v4

v4 is successful when at least one non-catalogue candidate reaches:

- target-pinned concrete schema,
- source-level root cause,
- candidate-specific reproduction artifact,
- measured non-fee economic delta or bounded TVS-at-risk,
- evidence grade 4,
- `qualifies_for_submission() == true`,
- human-gated `submission_alert.json`.

Until then, the correct operational stance is:

```text
0 submit_ready is acceptable if gates are blocking weak evidence.
Repeated catalogue or triage repros are not progress unless they generate new semantic candidates.
More trials are lower priority than better candidates and better verifiers.
```

---

## 26. Implementation Status - 2026-06-15

Implemented in v4.0.0:

- Target-pinned proposals and `bounty loop --target`; forced proposal/config mismatches fail before validation.
- HIPIF cron truth hardening; primary cron is no-agent deterministic full runner through final gate.
- Semantic recon package for Solidity, Rust/Solana, Anchor IDL, authority/value/oracle/bridge graphs, and candidate seeds.
- Concrete v4 candidate schema and upsert store at `data/security_results/knowledge/concrete_candidates.jsonl`.
- Opengrep/Semgrep-compatible rule directory and SARIF-to-candidate ingestion.
- Scoped off-chain recon wrappers for BBOT/SpiderFoot/Strix/Caido-style tools.
- Candidate-specific fail-closed PoC generation and verification for Foundry and Solana.
- KLend v2 instruction discriminator map, typed account roles, account diffs, probe result store, and failure classifiers.
- Wormhole economic-impact invariants, message fixtures, generated fail-closed economic PoCs, and submit gate enforcement for triage-only surfaces.
- Failure Trace RSI summarization into `failure_signatures.jsonl` and `refinement_hints.json`.
- v4 submit-ready gate requiring concrete candidate binding, source commit, selector/discriminator, reproduction artifact, and measured impact.

Verification:

- `pytest -k 'not api_serves_endpoints and not api_paginated_endpoint and not api_auth_rejects_without_key'` -> 385 passed, 5 skipped, 3 deselected.
- Full `pytest` is blocked in this sandbox only by local listening socket permission errors in the three API server tests.
- Wormhole semantic recon generated 606 production entrypoints and 559 bridge candidate seeds from `sources/wormhole/repo` commit `48258bc67e578830f47d28bd608323a72b11612c`.
- Full v4 HIPIF run completed 13/13 folds in 4820s with `gate_ok=true` and `submit_ready=false`.
- Focused cron/RSI tests passed: 57 passed.

Remaining operational work:

- Run real Opengrep/Semgrep once installed.
- Bind top Wormhole/KLend candidates to real deployed contracts/accounts and replace fail-closed generated PoCs with value-moving repros.
- Add native harnesses for current Cantina targets and a Cosmos SDK/CometBFT lane for dYdX.

## 27. Implementation Status - 2026-06-16

Implemented in v4.1.0:

- Added `src/night_shift_security/validation/self_interrogation.py`.
- Pipeline now runs a self-interrogation stage after ranking and before CPCV, Monte Carlo, fork, and Solana validation.
- Default config enables advisory conviction reports without hard filtering.
- HIPIF bounty-depth config enables small conviction-based rank pressure so stronger candidates reach top-N validation lanes first.
- Conviction reports are stamped into candidate vector metadata as `self_interrogation`, `conviction_score`, and `conviction_action`.

Verification:

- `pytest tests/test_self_interrogation.py tests/test_validation_layer.py tests/test_bounty_loop.py` -> 45 passed.
- `pytest tests/test_pipeline.py tests/test_structural_filters.py` -> 15 passed.
- Full v4.1 HIPIF run completed 13/13 folds in 4805s with `gate_ok=true` and `submit_ready=false`.

## 28. Implementation Status - 2026-06-16

Implemented in v4.2.0:

- Added deterministic Cyfrin Solodit API sync and pattern extraction.
- Added Solodit candidate metadata enrichment before self-interrogation.
- HIPIF `scan_all` now performs best-effort Solodit sync and pattern extraction; missing `CYFRIN_API_KEY` skips cleanly.
- Added repo-managed Hermes `solodit-research` skill and authenticated proposal cron recipe.
- Added `CYFRIN_API_KEY` placeholder to `.env.example`; the real key must remain local.

Verification:

- `pytest tests/test_solodit.py` -> 5 passed.
- Focused Solodit/self-interrogation/pipeline suite -> 66 passed.
- Sandbox-safe suite -> 391 passed, 5 skipped, 3 deselected.

## 29. Implementation Status - 2026-06-17

Implemented in v4.2.0 follow-up:

- Wormhole fork evidence now stamps `economic_impact_verified` using the same economic-impact helper that submission gates use.
- Triage-surface/no-delta Wormhole traces now become `missing_economic_impact` failure signatures with `generate_value_moving_poc` as the recommended RSI action.
- Recorded a local Wormhole no-delta trace under the ignored runtime trace store so refinement hints steer away from repeated governance-surface replay; the committed behavior is covered by classifier and fork-evidence tests.

Verification:

- Focused fork/failure/economic verifier suite: 28 passed.
- Expanded validation/bounty-loop/fork/failure/economic verifier suite: 68 passed.
- Full local pytest suite: 404 passed, 5 skipped.

## 31. Implementation Status - 2026-06-17

Implemented in v4.2.0 follow-up (AuditVault + Agent Lane + Lockdown):

- Added `src/night_shift_security/platform/auditvault.py` and three CLI subcommands: `platform auditvault-sync`, `platform auditvault-patterns`, `platform auditvault-summary`.
- Gitignored `sources/auditvault/` and ran an offline deterministic sync: 2383 findings, 826 protocols (slug x id pairs across 533 protocols); axis distribution: staking 141, oracle 115, bridge 72, amm 64, governance 57, lending 42, mev 28, perpetuals 9, messaging 5.
- Added `auditvault-research` Hermes skill (offline-only corpus research; never executes the chain or post processes) and installed as a symlink on the `nightsoul` profile.
- Locked the `nightsoul` profile to **20 NSS skill symlinks** (19 canonical + `auditvault-research`); deleted all unrelated skill directories. Assertions covered by unit test.
- Added Workstream A3 agent proposal lane bound to the `nightsoul` profile; restricted to xAI-OAuth + `grok-4.3` and the canonical 20-skill surface.
- Documented `metadata.trusted=false`, `severity_score=0.0` default, target restriction (NSS target universe), and lineage stamping (`auditvault_ref_unique_pattern_id`).
- Recorded a sample untrusted `data/security_results/hermes_proposals/auditvault-20260617.json` proposal (lineage: `f60cd87d0758` + `3365e69dc864`, target=wormhole, vector template=`token_account_dos`) and a lab notebook entry summarizing the agent turn.
- Verified a full no-agent HIPIF bounty-depth run to `chain_status=complete` over 13 folds; gate remains `submit_ready=false` and `gate_ok=true`.
- Verified trust-boundary integrity: `rg 'auditvault|audit_corpus' src/night_shift_security/validation/` returns no matches; `auditvault` is referenced only inside `platform/`, `pipelines/`, `hermes/skills/auditvault-research/`, and the audit/lab notebook artefacts - never inside `submission_gates`, `evidence_grading`, `novel_gate`, `klend`, `wormhole`, `nss-hipif-chain-run.py`, `hipif chain`, or `hipif bounty loop`.

Verification:

- `.venv/bin/python -m pytest -q` -> **438 passed, 5 skipped**.
- Focused AuditVault suite -> passed (sync, patterns, summary, no-key skip, gitignore, enrichment, lineage).
- Focused KLend loop suite -> passed.
- Focused Wormholescan + failure-trace RSI + task verifier + Wormhole economic suite -> 42 passed.

## 30. Implementation Status - 2026-06-17

Implemented in v4.2.0 follow-up:

- Added `foundry/test/WormholeValueProbe.t.sol`, a live mainnet-fork probe that attempts malformed `completeTransfer` as an attacker and asserts no USDC bridge-balance, attacker-balance, or `outstandingBridged(USDC)` delta.
- Added `wormhole-token-bridge-value-probe-ethereum` to the fork target registry and Wormhole fork/triage configs so composability-risk candidates can run a value/accounting probe before falling back to getter-only triage.
- Fork validation now treats `WORMHOLE_VALUE_PROBE` as fork-confirmed evidence without implying impact; task verifier and Wormhole economic gates still downgrade zero-delta results to `missing_economic_impact`.
- `HARNESS_AUTH_MOCKED=1` is a hard non-submittable marker: Wormhole economic gates reject mocked authorization even if the harness records a positive token delta.
- Added `src/night_shift_security/bridge/wormholescan.py` to fetch/decode Wormholescan signed VAAs, page through `/operations` with documented `page`/`pageSize`, select Ethereum-native release, uncompleted plain Ethereum-native release, Ethereum wrapped-mint, and asset-meta messages for replay, write route fixtures, and classify recent VAA corpora by route. `AUTHORIZED_REPLAY=1` is non-submittable unless a bridge accounting violation is also proven.

Verification:

- `.venv/bin/python -m pytest tests/test_wormholescan.py tests/test_fork.py tests/test_failure_trace_rsi.py tests/test_task_verifier.py tests/test_wormhole_economic.py -q` -> 42 passed.
- `.venv/bin/python -m pytest` -> 418 passed, 5 skipped.
- `forge test --match-path test/WormholeValueProbe.t.sol -vv` with `ETHEREUM_RPC_URL` loaded -> 2 passed, 3 optional route replays skipped by default.
- `fetch_operation_pages(pages=40, page_size=100)` + `build_real_vaa_corpus_report(...)` -> 3994 operations, 718 decoded token-bridge-shaped VAAs, route counts: 329 foreign wrapped mints, 119 Ethereum-native lock-outs, 146 plain Ethereum-native releases, 46 plain Ethereum wrapped mints, 38 Ethereum-native lock-out-with-payload routes, 33 Ethereum-native release-with-payload routes, 6 Ethereum wrapped-mint-with-payload routes, 1 asset metadata.
- Real native-release + wrapped-mint optional replay with extracted VAAs -> 2 passed, both already completed with zero delta and `BRIDGE_ACCOUNTING_VIOLATION:0`.
- `write_uncompleted_eth_native_release_vaa(pages=40, page_size=100)` can regenerate the pending plain payload-id 1 fixture; replay with `uncompleted_plain_eth_native_release.json` -> completed on fork with `TOKEN_DELTA:308414387625`, matching outstanding delta, and `BRIDGE_ACCOUNTING_VIOLATION:0`.
- Real asset-meta optional replay with extracted VAA -> skipped as same-chain Ethereum metadata before `createWrapped`.
