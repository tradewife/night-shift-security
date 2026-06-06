# Night Shift Security — Technical Specification

**Version:** 1.0  
**Date:** 2026-06-06  
**Author:** Grok (for Kate / tradewife)  
**Purpose:** Clone the Night Shift research engine architecture for parallel security and vulnerability research. This becomes a distinct but related track focused on surfacing protocol risks before they become exploits (inspired by the recent Zcash exploit news).

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