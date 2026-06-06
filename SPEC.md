# Night Shift Security — Technical Specification

**Version:** 1.0  
**Date:** 2026-06-06  
**Author:** Grok (for Kate / tradewife)  
**Purpose:** Clone the Night Shift research engine architecture for parallel security and vulnerability research. This becomes a distinct but related track focused on surfacing protocol risks before they become exploits (inspired by the recent Zcash exploit news).

---

## Agent Handover (Read This First)

**Workspace:** Open this repo — `/home/kt/projects/rtp/night-shift-security`  
**Remote:** https://github.com/tradewife/night-shift-security  
**Scope:** Security track only. Do **not** edit Night Shift Tokenomics (`/home/kt/projects/rtp/night-shift-tokenomics`) — a separate agent owns that repo per its own spec.

### Current status (2026-06-06)

Phase 4 shipped on `main`. **51 tests passing.** Foundry 1.7.1 installed.

| Commit | What shipped |
|--------|--------------|
| `ce813e6` | MVP pipeline, governance template, gates, exploit catalog |
| `01f84cd` | 4 attack templates, Darwinian evolution, 11-exploit catalog |
| `5768081` | Monte Carlo stress, Foundry simulator scaffold (mock fallback) |
| `d83cc3a` | CPCV/PBO overfitting detection, mainnet fork validation targets |
| `6de653a` | Public findings export, HTTP API, tokenomics bridge **producer** |
| `f7d4699` | Phase 3: 3 new templates, 16-exploit catalog, disclosure, API polish |
| *(this session)* | Phase 4: Foundry harness (7 tests), catalog seeds, 16/16 rediscovery, monitoring + bounty pipeline |

### Package layout (`src/night_shift_security/`)

```
core/          pipeline.py, evaluation, evolution, gates, scoring, results
domain/
  attack_templates/   governance_capture, treasury_drain, flash_loan_oracle, reentrancy,
                      composability_risk, upgradeability_risk, access_control_escalation
  simulators/         mock_simulator (default), foundry_simulator (forge + mock fallback)
data/          schemas.py, exploit_catalog.py (16 ground-truth exploits), fork_targets.py
validation/    historical_replay, monte_carlo_stress, foundry_validation, cpcv_stress, fork_validation
export/        dataset.py, loader.py, disclosure.py — severity-ranked JSON/JSONL + embargo redaction
api/           server.py, query.py — stdlib HTTP findings API with pagination/filtering
bridge/        tokenomics.py — exports tokenomics_risk_feed.json (consumer lives in tokenomics repo)
monitoring/    hooks.py — webhook + JSONL alert sinks for high-severity findings
bounty/        pipeline.py — Immunefi-style submission pack export
validation/    + catalog_seeds.py, rpc.py — ground-truth seeds + live RPC detection
cli/           main.py — run | serve | export | disclose | bounty | monitor
foundry/       VulnerableProtocol.sol (7 templates), AttackSimulation.t.sol, ForkHistorical.t.sol, setup.sh
```

### Pipeline as implemented

```
Stage 0: Ground-truth sanity (catalog exploits pass gates with known params)
Stage 1: Attack vector grid search (140 vectors across 7 templates)
Stage 3: Darwinian evolution (+12 candidates)
Stage 4b: CPCV + PBO overfitting detection (top 5 per template)
Stage 5: Monte Carlo stress (top 10)
Stage 5b: Foundry validation (top 5; mock if forge unavailable)
Stage 5c: Mainnet fork validation (Euler/Nomad EVM / Mango catalog; needs RPC for live bytecode)
Stage 2b: Rediscovery test vs 16-exploit catalog
Stage 6: Monitoring hooks (webhook / alerts.jsonl)
Stage 6b: Bug-bounty submission pack export
→ findings.json + report.md + public dataset + tokenomics bridge + bounty pack
```

**Last run metrics (Foundry 1.7.1, no RPC):** 118 findings, **16/16 rediscovery (gated)**, **5/5 foundry_confirmed**, monitoring alerts emitted to `alerts.jsonl`.

### Run locally

```bash
cd /home/kt/projects/rtp/night-shift-security
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m night_shift_security.cli.main          # full pipeline
.venv/bin/python -m night_shift_security.cli.main serve  # API on :8787
.venv/bin/pytest                                           # 51 tests
export PATH="$HOME/.foundry/bin:$PATH" && cd foundry && ./setup.sh && forge test
.venv/bin/python -m night_shift_security.cli.main disclose --input data/security_results/2026-06-06/findings.json --report
.venv/bin/python -m night_shift_security.cli.main bounty --input data/security_results/2026-06-06/findings.json
.venv/bin/python -m night_shift_security.cli.main monitor --input data/security_results/2026-06-06/findings.json
```

**Optional env for live fork tests:**
```bash
export ETHEREUM_RPC_URL=<your-rpc>   # or FOUNDRY_FORK_URL
cd foundry && ./setup.sh && forge test
```

### Outputs

Per-run (dated): `data/security_results/YYYY-MM-DD/findings.json`, `report.md`  
Always-updated API artifacts:
- `data/security_results/dataset/latest.json` — full severity-ranked feed
- `data/security_results/dataset/feed.json` — minimal API shape
- `data/security_results/dataset/findings.jsonl`
- `data/security_results/bridge/tokenomics_risk_feed.json` — cross-track bridge

**API endpoints** (`night-shift-security serve`):
`/api/v1/health` · `/api/v1/feed?page=1&limit=50&severity=critical` · `/api/v1/findings?template_id=composability_risk` · `/api/v1/findings/{id}` · `/api/v1/bridge/tokenomics`

Optional auth: set `NIGHT_SHIFT_API_KEY`; pass via `X-API-Key` header or `?api_key=`.

### RTP source (extraction reference)

Original Night Shift engine: `/home/kt/projects/tabs/resilient-token-protocol`  
Key file: `research/orchestration/night_shift.py` — patterns were adapted, not copied wholesale (no trading sim, OHLCV, perps, etc.).

### Cross-track bridge (producer side only)

Security **exports** `tokenomics_risk_feed.json` with `risk_patterns[]` (template triggers + penalties).  
Tokenomics has an optional consumer (`security_bridge` config) managed by another agent — do not modify tokenomics from this repo. If the bridge schema changes, coordinate with the tokenomics agent.

### Known limitations / gotchas

- **Foundry not required** — pipeline falls back to `mock_simulator` when `forge` is absent.
- **Fork validation** returns 0 confirmed without a real Ethereum RPC URL.
- **CPCV/PBO** is aggressive; many candidates get `DANGER` verdicts — intentional overfitting guard.
- **`data/security_results/`** is gitignored; re-export with `night-shift-security export --input <findings.json>`.
- **Governance fields** on `ContractState` have defaults so non-governance exploit fixtures construct cleanly.

### Suggested next work (Phase 5b / spec gaps)

1. Set `ETHEREUM_RPC_URL` (archive node) and make fork confirmation a scoring multiplier, not a hard gate.
2. Optional webhook via `NIGHT_SHIFT_WEBHOOK_URL` env (file-only default); Discord/Slack adapter later.
3. Tighten dedupe if needed (e.g. collapse generic `target_id=""` findings across protocols).
4. Integrate bounty pack with Immunefi/HackerOne submission APIs (currently file export only).
5. Rust Soulguard / on-chain invariant gates (secondary, per spec §0).

**Dedupe (Phase 5a):** Stage 5d canonical key = `template + params + protocol + primary_invariant`. Retroactive: `night-shift-security dedupe --input findings.json --re-export`. Sample: 118 → 111 on 2026-06-06 run.

### Config entry point

`src/night_shift_security/config/default.json` — templates, gates, darwinian, monte_carlo, foundry, cpcv, fork_validation thresholds.

---

## 0. Source Code Location & Extraction Instructions (Read This First)

**Critical:** Do not build Night Shift Security from scratch or from abstract description alone.

The original, working Night Shift implementation (and its supporting architecture) already exists inside the Resilient Token Protocol repository at:

**`/home/kt/projects/tabs/resilient-token-protocol`**

### Instructions for the AI Coding Agent:

1. **Navigate to the directory above** on the local machine.
2. **Explore the project structure** thoroughly, paying special attention to:
   - Any directories or files containing "night_shift", "research", "engine", "simulation", "backtest", "validation", "monte_carlo", "walk_forward", or "darwinian".
   - Python source files that implement parameter search, grid generation, evolutionary algorithms, scoring/fitness functions, or result analysis.
   - Configuration files, YAML/JSON schemas, or dataclasses that define searchable parameter spaces.
   - Data loading, historical windowing, and result persistence logic.
   - Any supporting utilities for parallel execution, logging, or structured output.

3. **Extract and deeply understand** these core reusable components (preserve their structure and philosophy):
   - The overall 5-stage research pipeline architecture
   - Grid / hypothesis space generation logic
   - Walk-forward validation harness (including fold creation and temporal splitting)
   - Darwinian / evolutionary population refinement code
   - Overfitting detection and robustness gates
   - Monte Carlo stress testing framework
   - Scoring / fitness evaluation system
   - Result storage, ranking, and reporting mechanisms

4. **Do NOT copy** trading-specific strategy parameters, perps logic, or Flash Trade integration unless they are genuinely reusable utilities.

5. **Preserve the engineering DNA:**
   - Massive parallel exploration (target 30k+ candidates)
   - Brutal, multi-gate validation before anything is accepted
   - Clear separation between in-sample discovery and out-of-sample validation
   - "Only survivors reach production" mindset
   - Red-team / adversarial orientation for the Security track (this is the key mindset shift)

6. After extraction and analysis, adapt the architecture as described in the rest of this specification for security and vulnerability research.

**Note:** There may also be Rust components (on-chain treasury program, Soulguard invariants). These are secondary for the research engine adaptation but may become relevant later when validating on-chain enforcement or invariant checking.

---

## 1. Overview & Goals

Night Shift proved it can explore enormous hypothesis spaces, apply rigorous validation, and reject fragile candidates using walk-forward testing, Darwinian evolution, and Monte Carlo methods.

**New Mission (Security edition):**
Apply the same high-throughput research engine to **security and economic attack surface analysis** on smart contracts and protocols.

Primary goals:
- Systematically discover and stress-test for vulnerabilities and economic attack vectors
- Validate security invariants and economic assumptions under adversarial conditions
- Surface high-risk patterns before mainnet deployment or large TVL
- Complement (not replace) traditional auditing, formal verification, and fuzzing
- Run in parallel with Night Shift Tokenomics under the same branded research platform

This directly addresses real incidents like the recent Zcash Orchard exploit and broader classes of DeFi attacks (flash loan manipulation, governance capture, reentrancy, oracle attacks, etc.).

---

## 2. Key Differences from Night Shift Tokenomics & Original Yield Engine

| Aspect                    | Tokenomics Edition                | Security Edition                          | Notes |
|---------------------------|-----------------------------------|-------------------------------------------|-------|
| **Primary Goal**          | Classify economic resilience      | Discover & validate attack surfaces       | Different objective |
| **Hypothesis Space**      | Tokenomic design parameters       | Attack vectors, invariant-breaking inputs, economic exploit parameters | Often more adversarial |
| **Data**                  | Historical on-chain token events  | Contract bytecode/ABIs, historical exploits, on-chain attack traces | New data sources |
| **Validation**            | Holder outcomes, value accrual    | Whether invariants hold or break under attack | Binary + severity scoring |
| **Simulation Style**      | Agent-based economic models       | Adversarial simulation + property-based testing | More "red team" mindset |
| **Output**                | Resilience Score + taxonomy label | Vulnerability report + severity + reproduction conditions | Actionable security artifacts |
| **Risk Profile**          | Overfitting to past narratives    | Missing novel/zero-day style attacks      | Different failure mode |

**Shared DNA (keep these):**
- Massive parallel hypothesis exploration (30k+ candidates)
- Walk-forward / temporal validation where applicable
- Darwinian refinement of attack strategies or parameter sets
- Monte Carlo stress testing
- Brutal rejection of fragile findings
- "Only survivors (or proven-dangerous vectors) are reported"

---

## 3. High-Level Architecture

Night Shift Security should follow a similar 5-stage pipeline but with a **red-team / adversarial** orientation:

```
Stage 1: Hypothesis Generation (Attack Vector + Parameter Space)
    ↓
Stage 2: Walk-Forward / Historical Exploit Validation
    ↓
Stage 3: Darwinian Evolution of Attack Strategies
    ↓
Stage 4: Invariant + Robustness Gates
    ↓
Stage 5: Full Adversarial Simulation + Property Testing
    ↓
→ Validated high-severity vulnerabilities + reproduction conditions + mitigation recommendations
```

---

### Stage 1: Hypothesis Generation (Attack Space)

Define searchable spaces for common (and emerging) vulnerability classes:

**Initial Vulnerability Categories (MVP scope):**
1. **Economic / Incentive Attacks**
   - Governance capture thresholds
   - Treasury drain via proposal + execution timing
   - Flash loan + price manipulation combinations
   - Oracle manipulation under low liquidity
   - Death spiral / bank run conditions in lending or stablecoin designs

2. **Smart Contract Implementation Flaws**
   - Reentrancy vectors (state changes after external calls)
   - Access control / role escalation paths
   - Integer overflow/underflow edge cases (where still relevant)
   - Unchecked return values or missing validations

3. **Cross-Contract / Composability Risks**
   - Dangerous interactions between multiple protocols (e.g., collateral + oracle dependencies)
   - Upgradeability / proxy risks
   - Shared liquidity pool manipulation across protocols

**Search Strategy:**
- Start with known exploit patterns from real incidents (Zcash, past DeFi hacks) encoded as templates
- Use mutation + crossover to generate variants
- Parameterize attack conditions (amounts, timing, state preconditions, actor behaviors)
- Support both fully automated generation and seeded "known dangerous" patterns

---

### Stage 2: Validation Against Historical Data + Known Exploits

- Replay or simulate historical attack conditions on target contracts
- Test whether the discovered vector would have succeeded on past vulnerable deployments
- Use on-chain traces from real exploits as ground truth for validation
- Walk-forward style: train attack generation on older incidents, validate on newer ones (temporal hold-out)

This gives credibility — "Night Shift Security rediscovered X known high-severity vectors and found Y new variants."

---

### Stage 3: Darwinian Evolution of Attacks

Evolve populations of attack strategies:
- Selection pressure = severity + reliability + generality (works across similar contract patterns)
- Mutation of parameters, timing, call sequences
- Crossover between different attack templates

This is where the engine can discover **novel combinations** that human auditors might miss (e.g., combining two medium-risk issues into a high-severity path).

---

### Stage 4: Invariant & Robustness Gates

Define what "survives" scrutiny:

**Gates:**
1. **Reproducibility** — Attack must succeed consistently under stated preconditions (not flaky)
2. **Severity Threshold** — Must cause meaningful economic loss, fund drainage, or governance takeover (not just theoretical)
3. **Generality** — Works on more than one specific contract instance (or clearly generalizable pattern)
4. **Stealth / Realism** — Feasible for a motivated but not superhuman attacker (capital requirements, timing, MEV competition considered)
5. **Invariant Violation** — Clearly breaks a stated or implicit security/economic invariant of the protocol

Designs/vectors that pass these gates are high-confidence findings worth reporting.

---

### Stage 5: Full Adversarial Simulation + Property-Based Testing

- Deploy the attack in a forked mainnet or high-fidelity test environment
- Combine with property-based testing (e.g., using Foundry's fuzzing or custom harnesses)
- Run Monte Carlo variations on timing, amounts, market conditions
- Measure blast radius (how much value can be extracted, how many users affected, governance impact)

**Output per Finding:**
- Clear reproduction steps / transaction sequence
- Preconditions and capital requirements
- Estimated severity (High / Critical) with justification
- Suggested mitigations or invariant additions
- Confidence score (how thoroughly it was validated)

---

## 4. Tech Stack & Implementation Notes

**Recommended:**
- **Python** for the core research orchestration (reuse Night Shift structure)
- **Foundry / Hardhat / Ape** for contract interaction, forking, and property testing
- **Heimdall / Slither / Mythril** or custom static analysis for initial contract ingestion
- **Agent-based or transaction-sequence simulator** for complex multi-step attacks
- Storage similar to Tokenomics track (results DB)

**Reuse from Original Night Shift:**
- Grid / evolutionary search engine
- Monte Carlo perturbation system
- Validation pipeline orchestration
- Result filtering / gate enforcement

**New / Heavier Lift:**
- Smart contract interaction layer
- Attack template library + mutation engine
- Historical exploit database / ground truth
- Severity + blast radius calculation
- Integration with on-chain monitoring (optional future: real-time alerting on discovered patterns)

---

## 5. Phased Delivery (Can Run in Parallel with Tokenomics Track)

**Phase 1 (MVP — 4–6 weeks)**
- Encode 3–5 common high-impact attack classes as searchable templates
- Build basic hypothesis generation + single-contract validation loop
- Validate against 5–10 known past exploits (re-discovery test)
- Manual review of top findings

**Phase 2 (Expansion)**
- Add Darwinian evolution of attack sequences
- Multi-contract / composability attack support
- Integration with property-based testing frameworks
- Automated severity scoring + report generation

**Phase 3 (Production Grade)**
- Public (or semi-public) findings feed
- Integration with builder / auditor workflows
- Cross-track insights (e.g., "this tokenomic design increases governance attack surface")
- Potential bug bounty / responsible disclosure pipeline

---

## 6. Risks & Mitigations

- **False positives / noise** — Strict gates + human review layer for high-severity claims. Start conservative.
- **Missing zero-days** — This engine is better at known classes + combinations than brand-new vulnerability types. Position it as a complement to audits and formal methods.
- **Legal / disclosure risk** — Clear responsible disclosure policy from day one. Do not publish live exploitable vectors without mitigation paths.
- **Computational cost** — Attack simulation on real contracts can be expensive. Prioritize high-TVL or high-risk targets first.
- **Scope creep** — Start narrow (e.g., governance + treasury attacks + flash loan vectors). Expand categories only after core loop is solid.

---

## 7. Success Criteria

- Night Shift Security re-discovers multiple known high-severity vulnerabilities with high fidelity
- Discovers at least one novel or non-obvious attack vector on a real protocol that passes all gates
- Produces clear, actionable reports that auditors or protocol teams can use
- Runs stably in parallel with the Tokenomics track without resource contention
- Contributes to the broader goal: making on-chain systems more robust through automated, rigorous research

---

## 8. Relationship to Night Shift Tokenomics

The two tracks are **parallel and distinct** but can share infrastructure and insights:

- Tokenomics track identifies designs that are economically fragile → Security track can prioritize those designs for deeper attack surface analysis
- Security track finds governance or treasury attack vectors → Tokenomics track can incorporate those as explicit failure modes in the Resilience Score
- Both benefit from the same core research engine architecture, branding ("Night Shift"), and "STFU and Build + rigorous validation" culture

This dual-track approach maximizes the leverage of the original Night Shift investment.

---

This spec is intentionally parallel in structure to the Night Shift Tokenomics spec so both can be developed with consistent methodology while staying focused on their respective domains.

---

**Summary for both specs:**
Night Shift started as a yield engine.  
It is now evolving into a **general-purpose agentic research platform** with specialized tracks for the two hardest problems in on-chain systems: **sustainable economics** and **security**.

Both specs are ready to be handed to an AI coding agent or developer. Let me know if you want any section expanded, turned into code scaffolding, or adjusted for specific constraints (budget, timeline, existing tooling).