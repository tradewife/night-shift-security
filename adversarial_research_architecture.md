# Night Shift Security — Adversarial Research Architecture (v3.1)

**Status:** Revised baseline (2026-06-14, SPEC v3.1.1)  
**Purpose:** Define a rigorous, programmable adversarial research engine optimized for bounty-grade security research.

---

## 1. Core intent

Night Shift Security produces high-leverage infrastructure for understanding protocol fragility. It generates attack hypotheses at scale, explores them with statistical discipline, and promotes only findings with clear evidence and reproducibility.

Priorities:
- Depth and rigor over volume
- Novel attack vectors over catalogue replay
- Strong provenance and auditability
- Outputs useful for builders and bounty programs

---

## 2. Key inspirations

Integrated patterns from high-signal adversarial audit work (Percolator Heist, closed-loop operator research) while preserving Night Shift philosophy.

**Integrated:**
- Systematic ranked hypothesis generation
- Novel vector focus (no obvious external shocks required)
- Tight loop: Hypothesis → Test → Validate → Refine
- Lab vs deployed reality distinction
- Operator scaffolding (v3.0): verifiers, checkpoints, N-trial scaling
- HIPIF folding (v3.1): compressed chain memory across night subgoals

**Rejected:**
- Unconstrained agentic exploration without gates
- LLM judgment for validation or prioritization

---

## 3. Layered architecture (v3.1)

| Layer | Name | Responsibilities |
|-------|------|------------------|
| 1 | Hypothesis Generation | Ranked generation, novel focus, `compose()`, bounded LLM (`metadata.trusted=false`) |
| 2 | Search & Optimization | Darwinian evolution, parameterized sampling, lineage |
| 3 | Simulation | Mock, Foundry, Solana fixture/validator/KLend harness |
| 3.5 | Operator Execution | Task verifier, Foundry/Slither MCP, Anvil sandbox, triage, oracle/TVS |
| 4 | Validation & Gates | Multi-axis scores, evidence grading 0–4, CPCV/PBO, credible harness gate |
| 5 | Scoring & Promotion | Bounty scoring, `submit_now`, human gate |
| 6 | Orchestration & Knowledge | Bounty loop, Coordinator, RSI, operator checkpoint, findings store |
| 6.5 | HIPIF Chain (v3.1) | Folded context, subgoal chain, repetition guard, lab notebook |

---

## 4. Hypothesis generation (Layer 1)

- Specialist generators per attack class (seven templates)
- `compose()` for chained attacks
- Bounded LLM via `llm_expansion` + Hermes proposals — always `validate_hypothesis()` gated
- Phase B: file triage 1–5, git patch mining, recon invariant PBT
- Wormhole: triage-scoped proposals (`nss-write-wormhole-triage-proposals.py`)

---

## 5. Validation & evidence (Layer 4)

**Multi-axis:** Likelihood, Impact, Stealth/Realism, Generality.

**Evidence grading:**
- Level 1: Structural + Monte Carlo survival
- Level 2: CPCV/PBO survival
- Level 3: Fork or validator reproduction
- Level 4: Root cause + reproducible impact artifacts

**Strict reproduction signals:**
- EVM: `fork_reproduced` (Foundry mainnet fork)
- Solana: `solana_reproduced` (`solana_fixture` or `solana_validator` or KLend `live_executed`)

**Operator task verifier (v3.0):** Novel candidates require `DELTA_WEI` / measured lamport delta when `required_for_novel: true`. Catalogue anchors exempt.

**Credible harness gate:** KLend fixture and fee-only CPI (`MEASURED_DELTA_LAMPORTS:0`) blocked from `submit_ready`.

**Lab vs deployed:** `deployed_viable`, `catalog_analogue`, reality-check fields on every finding.

---

## 6. Orchestration & knowledge (Layer 6)

### Bounty loop
`orchestration/bounty_loop.py` — scan → target pick → pipeline → `qualifies_for_submission()`. `--trials N` pins same target. `NSS_LOOP_DEPTH_SLUG` bypasses saturation for depth passes. `NSS_HIPIF_BOUNTY_DEPTH=1` boosts fork/solana top_n.

### Coordinator
Deterministic mission lifecycle; debrief → prioritize; no LLM in coordinator logic.

### RSI
`recursive_improvement.py` — store signals → refinement queue, cooldown, scan boost, plateaus.

### HIPIF chain (v3.1)
- **Skill:** `hermes/skills/hipif/SKILL.md`
- **Hooks:** `orchestration/hipif.py` — `parse`, `ground`, `record`, `fold`
- **Context:** `data/security_results/hipif/folded_context.json`
- **Deterministic runner:** `hermes/scripts/nss-hipif-chain-run.py` (bounty-depth profile)
- **Cron:** `nss-hipif-chain` daily 04:00 (agent); fallback `NSS_HIPIF_MODE=deterministic`

Bounty-depth subgoal flow:
```
scan → wormhole×12 → core/bridge refinement → KLend preflight → kamino×5
  → cantina slates → fork-ready hunt → RSI → refine → coordinator → gate
```

### Hermes trust boundary
Orchestrates CLI/MCP only. Proposals untrusted until Python gates pass. No autonomous external submission.

### Findings store
Append-only JSONL lineage at `knowledge/findings_store.jsonl`. Coordinator and RSI read; promotion flows through grading gates.

---

## 7. Operator layer (v3.0, shipped)

| Phase | Artifacts |
|-------|-----------|
| A | `task_verifier.py`, `operator_checkpoint.py`, `bounty loop --trials` |
| B | `triage/file_ranker.py`, `git_patches.py`, `invariants/pbt.py`, `run_klend_harness.py` |
| C | Foundry/Slither MCP, Docker Anvil, `operator/{foundry_tools,anvil_sandbox}.py` |
| D | `impact/oracle_arbitrage.py`, `impact/tvs_maximizer.py`, `operator-triage` skill |

---

## 8. Target surfaces (current)

| Target | Config | Harness |
|--------|--------|---------|
| Wormhole | `wormhole_triage.json`, `wormhole_shoestring.json` | Live core/bridge/pauser forks (`foundry/test/WormholeTriage.t.sol`) |
| Kamino KLend | `kamino_klend.json` | Validator clone + CPI probes (`solana/run_klend_harness.py`) |
| Cantina EVM | `euler_cantina.json` | Catalogue fork anchors (morpho, euler, pendle) |
| Immunefi scan | `bounty_scan/latest.json` | Unified Immunefi + Cantina ranking |

**Wormhole recon:** `sources/wormhole/recon.json` — live core/token_bridge IDs; Nomad analogue validation-only.

**KLend clones:** `sources/kamino/klend_accounts.json` — market/reserve/vault accounts for validator `--clone`.

---

## 9. Research loop

**Recon → Generate & Rank → Rapid Validation → Task Verify → Reality Check → Document & Refine**

With:
- Operator checkpoint on context rollover
- Lab notebook entry after every run (`lab-notebook` skill)
- HIPIF fold after each night subgoal
- Human gate on `submit_ready` only

---

## 10. Implementation priorities (2026-06-14)

1. **Novel `submit_ready`** — KLend `live_executed` + measured delta; Wormhole CPCV grade 3+ on non-catalogue survivors
2. **Hunt saturation fix** — fork-ready slugs reachable after depth passes in same chain
3. **HIPIF fold schema alignment** — runner folds match `CHAIN_SUBGOALS`
4. **Cantina live harness** — per-slug `targets/<slug>.json` beyond catalogue forks

See `AUDIT.md` for full gap list (P0–P3).

---

## 11. Documentation map

| Doc | Role |
|-----|------|
| `SPEC.md` | Version history, CLI, shipped features |
| `AUDIT.md` | System audit, gaps, artifact trust |
| `METHODOLOGY.md` | Research loop, evidence standards |
| `BOUNTY_RUN.md` | Operator command cookbook |
| `AGENTS.md` | Coding agent onboarding |

---

*This v3.1 document is the current architectural baseline.*