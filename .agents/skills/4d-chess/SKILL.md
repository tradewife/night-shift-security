---
name: 4d-chess
description: Use to achieve Grego-level deep security intelligence and adversarial multi-dimensional strategy in complex systems (esp. Solana DeFi protocols). Encodes "Deep Invariant Analysis" + reasoning architecture for tracing 7+ layers of interacting code/state/economic/temporal dependencies simultaneously, orchestrating parallel sub-agents for branch exploration, exploit path synthesis, and PoC generation. Elevates NSS patterns (ultrafuzz property fan-in, Crucible stateful invariants, codegraph structural mapping, fresh-context repetition, failure preservation, adjudication) with hybrid human-AI symbiosis: human provides protocol intent/judgment/"sacred assumptions" and mines signals from AI near-misses/false-positives; AI handles tireless breadth, depth, and combination search beyond human cognitive limits (~4-5 layers). Primary for breaking through audit ceilings on heavily reviewed protocols and generating high-impact, reproducible attack paths ready for bounty submission. "4D Chess" models the full adversarial state space across static structure, dynamic execution, economic incentives, and meta-timing/game layers.
---

# 4D Chess: Grego-Level Deep Invariant Reasoning & Multi-Dimensional Adversarial Strategy

This skill distills and elevates the core breakthroughs from Grego AI (Deep Invariant Analysis, reasoning architecture that pushes frontier models past their native limits, parallel sub-agent exploration, exploit path synthesis) into NSS-native form. It directly addresses the documented human cognitive ceiling of ~4-5 layers of system interactions where many critical bugs hide, while preserving and amplifying the human edges highlighted in the reflective analysis: judgment on protocol intent, asking the right directing questions, mining false positives/near-misses for signals, and maintaining attacker-minded distrust + pursuit of obscure edges.

**Sources mined (traceable)**:
- Primary technical thesis & $250k AI-found bounty case: https://x.com/0xriptide/status/2054201804536025152 (and thread) — "reasoning architecture... traces logic across 7+ layers... spins up connected sub-agents... Deep Invariant Analysis... mapped every module, every dependency, every interaction... traced execution paths looking for invariants".
- Reflective analysis on hybrid human-AI where humans still win: https://r.xyz/blog/i-was-out-hunted-by-my-own-ai-where-human-researchers-still-win-and-how-to-make-it-count — AI excels at breadth/depth/combinations/false-positive generation; humans excel at intent, judgment, question-asking, instinct, contextual teaching, mining signals from AI failures.
- Grego AI product: https://grego.ai/ — "reasons about your code the way an elite researcher does — tracing execution paths, identifying attack vectors... Deep Codebase Scanning... builds call graph + dataflow graph... invariant checks + state transition analysis... exploit path synthesis + PoC sketching... Built by security researchers... encoded that workflow".

**Hard-first prioritization**: The single most convoluted/highest-leverage subsystem is the **reasoning architecture + Deep Invariant Analysis engine** itself (the meta-layer that allows models to hold and trace complex logic across many interacting layers + orchestrate parallel specialized sub-agents). Everything else (PoC gen, reporting, hybrid loop) flows from it. We concentrate adaptation effort here first, then fan out to integrations and human symbiosis layer.

## Core Principles (Non-Negotiable — Grego + NSS Elevation)

- **Break the 4-5 Layer Ceiling**: Explicitly model and traverse 7+ layers of interactions (code internals + imported deps + state accounts + cross-program CPI + economic value flows + temporal ordering/race windows + meta-adversarial responses). Use recursive abstraction + verification gates so depth does not explode context.
- **Deep Invariant Analysis First**: Before any strategy or PoC, build and maintain a living map of "things that should never break" across all layers. Invariants are the chessboard; violations are the winning moves. Prioritize invariants with high blast-radius (economic impact, composability assumptions, trust boundaries).
- **Parallel Sub-Agent Orchestration with Central Adjudication**: Spin up specialized sub-agents (graph traversal, invariant proposer, economic modeler, state-transition explorer, PoC synthesizer, signal miner) that explore branches in parallel. Central "Chess Master" maintains global state, scores branches on 4D impact, prunes, merges insights, and enforces fresh-context where needed. Preserve *all* failure/near-miss artifacts across branches — they are high-signal (per Grego reflection on mining false positives).
- **Hybrid Human-AI Symbiosis (Humans Win on Judgment/Intent)**: AI owns tireless breadth, deep tracing, combination search, and initial PoC sketching. Human (via Day Shift/Hermes prompts or explicit injection) owns: protocol purpose/intent as "sacred high-level invariants", directing questions, marking intentional design tradeoffs, mining AI outputs for nearby real issues, final adjudication of complex findings, and instinct-driven hunches. The system improves by carrying context forward (teach once, applies everywhere).
- **4D State Space Modeling (NSS Ingenuity Elevation)**: Treat the protocol as a 4D+ chess position:
  1. **Static Structure Layer** (codegraph + AST/IDL/call-dataflow).
  2. **Dynamic Execution & State Transition Layer** (Crucible-style sequence mutation + simulation).
  3. **Economic/Value Flow Layer** (attacker profit max, tokenomics invariants, incentive misalignments).
  4. **Temporal/Meta-Game Layer** (reentrancy windows, multi-tx sequences, MEV/time-bandit opportunities, defender response anticipation).
  - Cross-layer impact scoring + "why this layer matters to the attack surface" traceability.
- **Attacker-Minded Distrust + Obscure Edge Pursuit**: Default stance: "distrust what the code claims to do, start from assets an attacker would target, follow interactions past the point where everyone else (and shallower tools) stopped looking." This transfers to both manual and AI-augmented paths.
- **Fresh-Context Repetition + Failure Preservation (NSS Native)**: Every deep branch or sub-agent exploration runs with fresh context (K attempts). All partial breaks, harness defects, near-miss invariants, and low-signal paths are preserved with full provenance before any pruning or "fix". Harness defects are often the signal to deeper issues.
- **Reproducible Exploit Path Synthesis + Submission-Ready Output**: Never stop at a flag. Always synthesize a minimal, reproducible attack story (multi-step, with exact conditions, state diffs, profit calc) + evidence package consumable by submission-reporting and bounty-loop gates.
- **Signal Mining from AI "Failures"**: Treat Grego-style false positives and partial invariant violations not as noise but as pointers to nearby real vulnerabilities or misunderstood assumptions. Dedicated "signal-miner" sub-process.

## When to Invoke

Use this skill for any target where:
- The protocol is heavily audited (3+ top firms) or has survived prior AI scans — i.e., where the 4-5 layer ceiling bugs live.
- High economic value or complex composability (DeFi primitives, cross-program interactions, oracles, bridges, tokenomics).
- You need to go deeper than standard ultrafuzz or codegraph alone (7+ layer interactions, subtle invariant breaks across deps).
- Generating or validating high-severity, reproducible attack paths/PoCs for bounty submission or internal certification.
- Running hybrid sessions where human judgment/intent must steer or validate AI depth (Day Shift planning, Hermes orchestration, or explicit "teach protocol intent" steps).
- Exploring "what if" adversarial scenarios or stress-testing assumptions in live or mirrored environments.
- Before claiming low FNR or "thoroughly hunted" on any non-trivial surface.

Mandatory first step for complex targets: codegraph explore (per AGENTS.md) → then 4d-chess deep invariant pass.

Do **not** use for trivial single-contract or already well-fuzzed surfaces where shallower tools suffice (start with ultrafuzz-discovery or operator-recon).

## Primary Workflow: Deep Invariant Analysis + 4D Branch Exploration (Hard-First Core)

**Phase 0: Ingestion & Structural Foundation (codegraph-x-ray + Grego Deep Scan)**
- Ingest full repo + deps + IDL/build config (Solana Anchor priority; generalize to Move/EVM later).
- Build enhanced call graph + dataflow + account/state graph (extend codegraph-x-ray outputs).
- Identify trust boundaries, external calls, state mutations, economic primitives (mints, burns, swaps, oracles).
- Output: Layered system map with initial "candidate invariants" (things that should hold across layers).

**Phase 1: Deep Invariant Proposal & Cross-Layer Tracing (The 7+ Layer Engine)**
- For each high-blast-radius area, launch invariant proposer sub-agent(s).
- Trace execution paths looking for invariants that "should never break but might under specific conditions" (Grego phrasing).
- Explicitly cross  layers: e.g., a state transition in one program that violates an economic assumption in a dependent protocol, or a temporal window that allows value extraction across CPI + reentrancy.
- Use recursive decomposition: Summarize deep sub-systems with traceable "impact on parent invariant" + verification gate (does the summary preserve the violation signal?).
- Maintain living invariant table (fan-in style, but 4D-enriched): Invariant | Layers affected | Blast radius (econ + composability) | Evidence so far | Status (holding / candidate break / confirmed break).

**Phase 2: Parallel Sub-Agent Orchestration (The Reasoning Architecture)**
- Central Chess Master (orchestrator) spawns specialized sub-agents based on Phase 1 signals:
  - Graph/Traversal Agent: Deepens call/dataflow paths.
  - State-Transition / Crucible Agent: Mutates sequences, checks state invariants (integrate Crucible directly for Solana .so targets).
  - Economic Modeler Agent: Quantifies attacker profit, value flow disruptions, incentive attacks.
  - Temporal/Meta Agent: Explores multi-tx, reentrancy windows, ordering attacks, anticipated defender moves.
  - PoC Synthesizer Agent: Turns promising breaks into minimal reproducible scripts + sandbox execution.
  - Signal Miner Agent: Analyzes all "failures", partial breaks, and Grego-style false positives for nearby real signals or intent misunderstandings.
- Each sub-agent runs with fresh-context repetition (K=3–5) where stochastic.
- All artifacts (prompts, outputs, partial states, logs, PoC attempts) preserved in structured failure/ or branch/ dirs with full provenance.
- Central adjudicator scores branches on 4D impact (severity × reproducibility × blast radius × novelty), merges insights, prunes dead branches, and feeds high-signal failures back to invariant table or new sub-agents.

**Phase 3: Human Symbiosis & Intent Injection (Where Humans Win)**
- At key gates (after initial map, after promising invariant breaks, before final PoC): Human reviews via Day Shift / Hermes or explicit prompts.
- **Intent Injection**: Human provides "protocol constitution" — high-level sacred assumptions, intended behaviors, design tradeoffs, team goals. These become meta-invariants that guide pruning and prioritization (e.g., "slippage param is intentionally unset for UX; do not flag as front-running unless it enables >X profit drain").
- **Question Direction**: Human asks directing questions that focus AI depth (e.g., "what happens to invariant Y if oracle Z delays by 2 slots under high MEV?").
- **Signal Mining Partnership**: Human + Signal Miner review AI near-misses/false-positives together; human intuition often spots the "real issue nearby".
- **Final Adjudication**: Human validates complex findings, confirms reproducibility on mirror/fork, sizes impact, and decides submission path.
- Context is carried forward: Marked intentional findings update the living map so future runs respect them.

**Phase 4: Exploit Path Synthesis & Bounty-Ready Output**
- For every confirmed break: Synthesize minimal attack story (step-by-step, exact preconditions, state diffs, profit calc, tx sequence).
- Generate PoC (Anchor/Solana tx builder or Foundry-style where applicable) + sandbox validation.
- Produce submission package: structured report, evidence, reproducible artifacts (integrates directly with submission-reporting skill).
- Update invariant table and global map with the new confirmed violation + any new context.

**Phase 5: Persistent Loop & Improvement (NSS Native)**
- All runs feed recursive-improvement and hypothesis-expansion.
- Failures and near-misses spawn new 4D branches or property refinements for ultrafuzz.
- Periodic re-runs on evolved codebase (post-patch) to hunt regressions or second-order effects.
- Track "layers reached" and "invariants maintained/broken" as meta-metrics of depth achieved.

## Integration with Existing NSS Skills & Architecture (Strengthen, Don't Duplicate)

- **codegraph-x-ray**: Mandatory Phase 0 input. 4d-chess consumes and enriches its structural invariants with dynamic/economic/temporal layers.
- **ultrafuzz-discovery**: Complementary. Use 4d-chess to identify high-value property fan-in targets (the deep invariants); ultrafuzz executes high-volume attempts. 4d-chess can propose new properties from cross-layer signals. Fresh-context repetition is shared.
- **Crucible (sources/crucible/repo)**: Primary engine for Solana stateful sequence invariants inside State-Transition sub-agent. 4d-chess orchestrates when/how to invoke it within broader 4D exploration.
- **bounty-loop + submission-reporting**: 4d-chess outputs feed directly — attack paths, PoCs, evidence grading. Add "4d-chess certified depth: 7+ layers / X invariants broken" as high-evidence signal for submit_now gates.
- **hypothesis-expansion + recursive-improvement**: Consume 4d-chess signals (new invariant breaks, interesting failures) as structured seeds for proposal generation and refinement queues.
- **onchain-asset-tracing / operator-***: Use for post-exploit forensics or validating economic impact of synthesized paths. 4d-chess can incorporate live on-chain state into economic layer modeling.
- **lab-notebook / operator-checkpoint**: Log all 4d-chess sessions with full artifact manifests, layer depth achieved, human intent injections, and adjudication notes. Treat as first-class research artifacts.
- **auditvault-research / solodit-research**: Historical findings can seed initial invariant tables or "known hard edges" for 4d-chess to re-examine at greater depth.
- **Day Shift / Night Shift / Hermes**: Day Shift uses 4d-chess for deep planning and intent injection on high-value targets. Night Shift cron can run autonomous 4d-chess passes (with human intent pre-loaded). Hermes can orchestrate multi-agent 4d-chess sessions.

Cross-reference AGENTS.md: Hard-First Principle, Persistent Looping Discipline, ultrafuzz mandatory before honest-zero claims, operator skills table, skills in .agents/skills/ and hermes/skills/.

## 4D Chess Ingenuity Elevations (Beyond Direct Grego Lift)

- **Explicit 4D State Space**: Formal (lightweight) modeling of the four layers with cross-impact matrices. Makes "why this deep interaction matters" auditable and prioritizable.
- **Recursive Layer Summarization with Verification Gates**: To scale past 7 layers without context explosion — each deep sub-system summarized with "preserves/violates parent invariant X because Y" + gate check before ascending.
- **Economic Layer as First-Class**: Always quantify attacker profit and protocol loss in invariant breaks (ties directly to bounty value and submission impact sizing).
- **Meta-Game Layer (Anticipatory)**: Sub-agent that models "if this invariant breaks and protocol patches naively, what second-order attack opens?" — pushes beyond static analysis into dynamic adversarial foresight.
- **Signal-from-Failure as Core Loop**: Dedicated persistent process (inspired by Grego reflection) that treats every AI false positive, partial break, and harness defect as a pointer. Often leads to the real obscure edge.
- **Intent as Executable Meta-Invariants**: Human-provided protocol purpose is compiled into machine-checkable high-level invariants that prune irrelevant branches and elevate intent-respecting findings.
- **Hybrid Certification Gate**: No high-severity claim or submission without documented human intent review + 4d depth metric + reproducible PoC. Strengthens existing adjudication.

## Anti-Patterns to Avoid

- Treating 4d-chess as pure autonomous replacement for human judgment (the blog post exists precisely because the creators were "out-hunted" yet still see human edges as decisive).
- Shallow layer traversal or stopping at first invariant break without cross-layer and economic impact.
- Discarding AI near-misses/false-positives without running the signal-miner.
- Ignoring human intent injection — leads to flagging deliberate design tradeoffs (classic Grego AI limitation without context).
- Running without fresh-context repetition or failure preservation on deep branches.
- Claiming "thorough" without measuring layers traversed and invariants stress-tested.
- Using on live mainnet without mirror/fork validation + human oversight (even Grego outputs were human-validated before reporting).

## Output & Provenance Standards

Every 4d-chess run must produce:
- Structured invariant map + 4D impact scores.
- Full branch/artifact tree (preserved even for pruned paths).
- Synthesized attack story + reproducible PoC + evidence package (submission-ready).
- Human intent injection log + adjudication notes.
- Meta-metrics: max layers reached, invariants broken/held, signals mined from failures, human-AI division of labor.
- Traceability: git SHAs of target, codegraph output, Crucible version, 4d-chess skill version, sub-agent prompts/outputs, human review artifacts.
- Update to lab-notebook and relevant SPEC.md / AGENTS notes if new patterns emerge.

## Quick-Start Example: Heavily Audited Solana DeFi Protocol

1. codegraph explore --target <protocol> --depth 4 (structural foundation).
2. Invoke 4d-chess with human-provided "protocol intent" (e.g., "Core invariant: user deposits are always withdrawable 1:1 minus fees under normal conditions; oracle updates are trusted but with staleness checks").
3. Phase 1–2: Deep invariant tracing across 7+ layers (program logic + CPI to token program + state PDA mutations + economic share calculations + reentrancy windows + potential MEV ordering).
4. Parallel sub-agents explore branches; Signal Miner flags an interesting near-miss around a dependency interaction.
5. Human reviews promising break + intent injection confirms it's not a deliberate tradeoff.
6. PoC Synthesizer + Crucible sub-agent produces validated multi-tx attack draining X% of TVL.
7. Output full attack story, PoC, $ impact calc → submission-reporting.
8. Preserve everything; feed new invariant violation back to ultrafuzz property fan-in for regression hunting.

This skill was produced via alpha-miner elevation of Grego AI alpha (Deep Invariant Analysis + reasoning architecture + hybrid insights) into NSS. It preserves source fidelity while adding 4D modeling, recursive depth scaling, economic/meta layers, tight Crucible/ultrafuzz integration, and explicit human symbiosis gates that make the "humans still win" thesis operational. No invention of core mechanisms — rigorous adaptation and cross-connection to existing NSS rigor.

**Implementation note**: Added via alpha-miner on Grego AI sources (X post 2054201804536025152, r.xyz blog, grego.ai). Hard-first on reasoning architecture + Deep Invariant Analysis as Primary Alpha. See .agents/skills/4d-chess/SKILL.md. Strengthens ultrafuzz/Crucible/codegraph/bounty-loop with 7+ layer multi-dimensional adversarial intelligence and hybrid judgment layer. Trigger: alpha-miner on grego sources + "extract a skill we'll call 4d chess".

---

**End of 4D Chess SKILL.md**
