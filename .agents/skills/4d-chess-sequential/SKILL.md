---
name: 4d-chess-sequential
description: Sequential single-threaded variant of 4d-chess for rate-limited and free-tier environments. Achieves full Grego-level deep security intelligence and adversarial multi-dimensional strategy in complex systems (esp. Solana DeFi protocols) without any sub-agents or parallelism. Uses iterative deepening, layer-by-layer and dimension-by-dimension sequential exploration, aggressive summarization, and self-refinement loops to maintain complete depth. Encodes "Deep Invariant Analysis" + reasoning architecture for tracing 7+ layers of interacting code/state/economic/temporal dependencies. Elevates NSS patterns (ultrafuzz property fan-in, Crucible stateful invariants, codegraph structural mapping, fresh-context repetition, failure preservation, adjudication) with hybrid human-AI symbiosis: human provides protocol intent/judgment/"sacred assumptions" and mines signals from AI near-misses/false-positives; the single agent handles tireless breadth, depth, and combination search beyond human cognitive limits (~4-5 layers) via controlled sequential steps. Primary for breaking through audit ceilings on heavily reviewed protocols while respecting API quotas. "4D Chess" models the full adversarial state space across static structure, dynamic execution, economic incentives, and meta-timing/game layers. Optimized to take longer but never sacrifice rigor or coverage.
---

# 4D Chess (Sequential): Grego-Level Deep Invariant Reasoning & Multi-Dimensional Adversarial Strategy — Rate-Limited Edition

This is the sequential, single-threaded variant of the 4d-chess skill. It distills and elevates the core breakthroughs from Grego AI (Deep Invariant Analysis, reasoning architecture that pushes frontier models past their native limits, exploit path synthesis) into NSS-native form **without any parallel sub-agents**. All exploration, adjudication, and synthesis happens sequentially within a single agent process. Depth is fully preserved through iterative deepening, layer-by-layer processing, recursive self-refinement, and aggressive context summarization. This version is specifically designed for rate-limited subscriptions and free-tier environments: it minimizes concurrent tool/API calls, controls token usage via summarization, and spaces out operations naturally.

It directly addresses the documented human cognitive ceiling of ~4-5 layers of system interactions where many critical bugs hide, while preserving and amplifying the human edges highlighted in the reflective analysis: judgment on protocol intent, asking the right directing questions, mining false positives/near-misses for signals, and maintaining attacker-minded distrust + pursuit of obscure edges.

**Sources mined (traceable)**:
- Primary technical thesis & $250k AI-found bounty case: https://x.com/0xriptide/status/2054201804536025152 (and thread) — "reasoning architecture... traces logic across 7+ layers... Deep Invariant Analysis... mapped every module, every dependency, every interaction... traced execution paths looking for invariants".
- Reflective analysis on hybrid human-AI where humans still win: https://r.xyz/blog/i-was-out-hunted-by-my-own-ai-where-human-researchers-still-win-and-how-to-make-it-count — AI excels at breadth/depth/combinations/false-positive generation; humans excel at intent, judgment, question-asking, instinct, contextual teaching, mining signals from AI failures.
- Grego AI product: https://grego.ai/ — "reasons about your code the way an elite researcher does — tracing execution paths, identifying attack vectors... Deep Codebase Scanning... builds call graph + dataflow graph... invariant checks + state transition analysis... exploit path synthesis + PoC sketching... Built by security researchers... encoded that workflow".

**Hard-first prioritization**: The single most convoluted/highest-leverage subsystem is the **reasoning architecture + Deep Invariant Analysis engine** itself (the meta-layer that allows models to hold and trace complex logic across many interacting layers using sequential iterative deepening and self-refinement). Everything else (PoC gen, reporting, hybrid loop) flows from it. We concentrate adaptation effort here first, then fan out to integrations and human symbiosis layer. Parallelism is deliberately removed to respect rate limits while retaining equivalent (or greater) rigor through controlled depth-first and priority-based sequential traversal.

## Core Principles (Non-Negotiable — Grego + NSS Elevation)

- **Break the 4-5 Layer Ceiling**: Explicitly model and traverse 7+ layers of interactions (code internals + imported deps + state accounts + cross-program CPI + economic value flows + temporal ordering/race windows + meta-adversarial responses). Use recursive abstraction + verification gates so depth does not explode context. Depth is achieved sequentially via iterative deepening loops rather than parallelism.
- **Deep Invariant Analysis First**: Before any strategy or PoC, build and maintain a living map of "things that should never break" across all layers. Invariants are the chessboard; violations are the winning moves. Prioritize invariants with high blast-radius (economic impact, composability assumptions, trust boundaries).
- **Sequential Iterative Deepening & Single-Agent Adjudication (Rate-Limited Optimized)**: The agent performs all exploration, branch evaluation, and adjudication sequentially in a single thread. It maintains a persistent working state (invariant table, 4D branch log, impact scores, layer summaries) across steps via explicit logging and summarization. Uses multi-step internal reasoning chains, depth-first or priority-based sequential branch exploration, and self-refinement loops to simulate the depth and breadth previously achieved with parallel sub-agents. Each layer and 4D dimension is processed fully before advancing. Fresh-context is enforced by periodic context resets with concise summaries of prior work. All artifacts (including near-misses and partial paths) are preserved sequentially in structured logs/files. This trades execution time for dramatically lower concurrent resource usage — ideal for rate-limited and free-tier subscriptions.
- **Hybrid Human-AI Symbiosis (Humans Win on Judgment/Intent)**: The single agent owns tireless breadth, deep tracing, combination search, and initial PoC sketching via sequential steps. Human (via Day Shift/Hermes prompts or explicit injection) owns: protocol purpose/intent as "sacred high-level invariants", directing questions, marking intentional design tradeoffs, mining AI outputs for nearby real issues, final adjudication of complex findings, and instinct-driven hunches. The system improves by carrying context forward (teach once, applies everywhere). Human checkpoints also serve as natural pacing controls for rate limits.
- **4D State Space Modeling (NSS Ingenuity Elevation)**: Treat the protocol as a 4D+ chess position:
  1. **Static Structure Layer** (codegraph + AST/IDL/call-dataflow).
  2. **Dynamic Execution & State Transition Layer** (Crucible-style sequence mutation + simulation).
  3. **Economic/Value Flow Layer** (attacker profit max, tokenomics invariants, incentive misalignments).
  4. **Temporal/Meta-Game Layer** (reentrancy windows, multi-tx sequences, MEV/time-bandit opportunities, defender response anticipation).
  - Cross-layer impact scoring + "why this layer matters to the attack surface" traceability.
- **Attacker-Minded Distrust + Obscure Edge Pursuit**: Default stance: "distrust what the code claims to do, start from assets an attacker would target, follow interactions past the point where everyone else (and shallower tools) stopped looking." This transfers to both manual and AI-augmented paths.
- **Fresh-Context Repetition + Failure Preservation (NSS Native)**: Every deep exploration step, branch, or refinement iteration runs with fresh-context repetition (K attempts) where stochastic or high-uncertainty. All partial breaks, harness defects, near-miss invariants, and low-signal paths are preserved with full provenance before any pruning or "fix". Harness defects are often the signal to deeper issues.
- **Reproducible Exploit Path Synthesis + Submission-Ready Output**: Never stop at a flag. Always synthesize a minimal, reproducible attack story (multi-step, with exact conditions, state diffs, profit calc) + evidence package consumable by submission-reporting and bounty-loop gates.
- **Signal Mining from AI "Failures" (Sequential Core Loop)**: Treat Grego-style false positives and partial invariant violations not as noise but as pointers to nearby real vulnerabilities or misunderstood assumptions. Dedicated sequential signal-mining step performed after each major layer or dimension.

## When to Invoke

Use this skill for any target where:
- The protocol is heavily audited (3+ top firms) or has survived prior AI scans — i.e., where the 4-5 layer ceiling bugs live.
- High economic value or complex composability (DeFi primitives, cross-program interactions, oracles, bridges, tokenomics).
- You need to go deeper than standard ultrafuzz or codegraph alone (7+ layer interactions, subtle invariant breaks across deps).
- Generating or validating high-severity, reproducible attack paths/PoCs for bounty submission or internal certification.
- Running hybrid sessions where human judgment/intent must steer or validate AI depth (Day Shift planning, Hermes orchestration, or explicit "teach protocol intent" steps).
- Exploring "what if" adversarial scenarios or stress-testing assumptions in live or mirrored environments.
- Before claiming low FNR or "thoroughly hunted" on any non-trivial surface.
- **Especially when operating under rate limits, quota constraints, or free-tier conditions** where any form of parallelism or concurrent tool calls would risk overloading or throttling.

Mandatory first step for complex targets: codegraph explore (per AGENTS.md) → then 4d-chess-sequential deep invariant pass.

Do **not** use for trivial single-contract or already well-fuzzed surfaces where shallower tools suffice (start with ultrafuzz-discovery or operator-recon).

## Primary Workflow: Deep Invariant Analysis + Sequential 4D Iterative Exploration (Hard-First Core)

**Phase 0: Ingestion & Structural Foundation (codegraph-x-ray + Grego Deep Scan)**
- Ingest full repo + deps + IDL/build config (Solana Anchor priority; generalize to Move/EVM later).
- Build enhanced call graph + dataflow + account/state graph (extend codegraph-x-ray outputs).
- Identify trust boundaries, external calls, state mutations, economic primitives (mints, burns, swaps, oracles).
- Output: Layered system map with initial "candidate invariants" (things that should hold across layers). Produce an initial "Phase 0 Summary" for carry-forward.

**Phase 1: Deep Invariant Proposal & Cross-Layer Tracing (The 7+ Layer Engine)**
- The agent proposes and traces invariants that "should never break but might under specific conditions" (Grego phrasing), starting from high-blast-radius areas identified in Phase 0.
- Explicitly cross layers sequentially: e.g., a state transition in one program that violates an economic assumption in a dependent protocol, or a temporal window that allows value extraction across CPI + reentrancy.
- Use recursive decomposition: For deep sub-systems, summarize with traceable "impact on parent invariant X because Y" + verification gate (does the summary preserve the violation signal?).
- Maintain living invariant table (fan-in style, but 4D-enriched): Invariant | Layers affected | Blast radius (econ + composability) | Evidence so far | Status (holding / candidate break / confirmed break).
- After completing initial cross-layer tracing, produce a concise "Phase 1 Summary" (key candidate invariants, high-priority areas, initial cross-impacts) to keep context manageable.

**Phase 2: Sequential 4D Iterative Exploration (Single-Threaded Reasoning Architecture)**
The agent acts as its own orchestrator and adjudicator. All work is sequential, one focused step at a time, with explicit state updates and summarization after each major block to control context length and token consumption. This achieves equivalent (or superior) depth to parallel approaches by using priority-based ordering, depth-first traversal of promising branches, iterative refinement loops, and verification gates.

- **Step 2.0: Initialize Global State**
  - Load Phase 0 + Phase 1 outputs.
  - Create/maintain:
    - Invariant Table (living document)
    - 4D Branch Log (all explored paths, partial results, near-misses)
    - 4D Impact Scores (severity × reproducibility × blast radius × novelty)
    - Layer Summaries (one per dimension processed)
  - Prioritize order: Start with highest-blast-radius invariants, then process 4D dimensions in logical sequence (Static → Dynamic → Economic → Temporal/Meta), with cross-references as needed.

- **Step 2.1: Static Structure Layer Deepening (Sequential)**
  - Using Phase 0 graph + fresh reasoning, deepen call/dataflow paths for high-priority invariants.
  - Generate candidate branches sequentially.
  - For each candidate: Evaluate against invariants, score on 4D impact, decide (deepen further with focused sub-chain, log as near-miss, or prune).
  - Use depth-first: Fully explore one high-potential static path (with recursive summarization) before moving to the next.
  - After completing the layer: Produce "Static Layer Summary" + update Global State. Perform quick signal-mining pass on recent outputs.

- **Step 2.2: Dynamic Execution & State Transition Layer (Sequential, Crucible Integration)**
  - Build on Static Layer Summary + Global State.
  - For promising dynamic paths, invoke Crucible (or equivalent simulation) sequentially on key sequences identified so far.
  - Generate and evaluate state-transition violations one at a time.
  - Apply fresh-context repetition (K attempts) on uncertain mutations.
  - Integrate previous layers' findings (e.g., how a static call chain enables a state break).
  - After layer: "Dynamic Layer Summary" + Global State update + signal mining.

- **Step 2.3: Economic/Value Flow Layer (Sequential)**
  - Using accumulated summaries + Global State, model attacker profit, value flows, incentive misalignments.
  - Quantify impact of candidate breaks sequentially (e.g., "this invariant violation enables X token drain under Y conditions").
  - Score and refine previous branches with economic lens.
  - Produce "Economic Layer Summary" + update state + signal mining.

- **Step 2.4: Temporal/Meta-Game Layer (Sequential, Anticipatory)**
  - Final dimension: Explore reentrancy windows, multi-tx sequences, MEV opportunities, and defender-response anticipation.
  - Model "if this invariant breaks and protocol patches naively, what second-order attack opens?" using accumulated context.
  - Sequential evaluation of temporal branches.
  - Produce "Temporal/Meta Layer Summary" + final Global State consolidation.

- **Step 2.5: Cross-Layer Synthesis & Iterative Refinement Loop**
  - Review all layer summaries and Global State.
  - Run one or more iterative refinement passes: Re-examine high-scoring branches with full 4D context (using summary + key excerpts for freshness).
  - Deepen any remaining high-potential areas via additional focused sequential iterations.
  - Final signal-mining sweep across everything logged.
  - Prune low-value branches only after full documentation.

- **Pacing & Rate-Limit Controls (Built-in)**:
  - Limit tool invocations (codegraph, Crucible, etc.) to one major call per layer/step where possible.
  - Use aggressive summarization after every layer and major branch.
  - Insert natural human-review gates between layers if desired (or run fully autonomously with summaries).
  - Context management: When approaching limits, explicitly summarize prior work and continue with "Summary + Current Focus" prompt.
  - All operations are strictly sequential — no concurrent calls.

**Phase 3: Human Symbiosis & Intent Injection (Where Humans Win)**
- At key gates (after Phase 0/1, after each major layer in Phase 2, before final synthesis): Human reviews via Day Shift / Hermes or explicit prompts.
- **Intent Injection**: Human provides "protocol constitution" — high-level sacred assumptions, intended behaviors, design tradeoffs, team goals. These become meta-invariants that guide prioritization and refinement (e.g., "slippage param is intentionally unset for UX; do not flag as front-running unless it enables >X profit drain").
- **Question Direction**: Human asks directing questions that focus the sequential depth (e.g., "what happens to invariant Y if oracle Z delays by 2 slots under high MEV?").
- **Signal Mining Partnership**: Human reviews the agent's sequential signal-mining outputs and near-misses; human intuition often spots the "real issue nearby".
- **Final Adjudication**: Human validates complex findings, confirms reproducibility on mirror/fork, sizes impact, and decides submission path.
- Context is carried forward: Marked intentional findings update the living map and Global State so future runs (or iterations) respect them.

**Phase 4: Exploit Path Synthesis & Bounty-Ready Output**
- For every confirmed break (after human adjudication): Synthesize minimal attack story (step-by-step, exact preconditions, state diffs, profit calc, tx sequence) using the full accumulated Global State and layer summaries.
- Generate PoC (Anchor/Solana tx builder or Foundry-style where applicable) + sandbox validation (sequential).
- Produce submission package: structured report, evidence, reproducible artifacts (integrates directly with submission-reporting skill).
- Update invariant table, Global State, and all summaries with the new confirmed violation + any new context.

**Phase 5: Persistent Loop & Improvement (NSS Native)**
- All runs feed recursive-improvement and hypothesis-expansion.
- Failures, near-misses, and signal-mining outputs spawn new 4D branches or property refinements for ultrafuzz (via sequential re-runs or targeted follow-ups).
- Periodic re-runs on evolved codebase (post-patch) to hunt regressions or second-order effects.
- Track "layers reached", "invariants maintained/broken", and "sequential iterations performed" as meta-metrics of depth achieved.

## Integration with Existing NSS Skills & Architecture (Strengthen, Don't Duplicate)

- **codegraph-x-ray**: Mandatory Phase 0 input. 4d-chess-sequential consumes and enriches its structural invariants with dynamic/economic/temporal layers via sequential processing.
- **ultrafuzz-discovery**: Complementary. Use 4d-chess-sequential to identify high-value property fan-in targets (the deep invariants); ultrafuzz executes high-volume attempts. 4d-chess-sequential can propose new properties from cross-layer signals discovered sequentially. Fresh-context repetition is shared.
- **Crucible (sources/crucible/repo)**: Invoked sequentially by the main 4d-chess-sequential agent within the Dynamic Execution & State Transition Layer step. Provides stateful sequence invariants for Solana targets.
- **bounty-loop + submission-reporting**: 4d-chess-sequential outputs feed directly — attack paths, PoCs, evidence grading. Add "4d-chess-sequential certified depth: 7+ layers / X invariants broken / Y sequential iterations" as high-evidence signal for submit_now gates.
- **hypothesis-expansion + recursive-improvement**: Consume 4d-chess-sequential signals (new invariant breaks, interesting failures, signal-mining outputs) as structured seeds for proposal generation and refinement queues.
- **onchain-asset-tracing / operator-***: Use for post-exploit forensics or validating economic impact of synthesized paths. 4d-chess-sequential can incorporate live on-chain state into economic layer modeling (sequentially).
- **lab-notebook / operator-checkpoint**: Log all 4d-chess-sequential sessions with full artifact manifests, layer summaries, human intent injections, sequential execution trace, and adjudication notes. Treat as first-class research artifacts.
- **auditvault-research / solodit-research**: Historical findings can seed initial invariant tables or "known hard edges" for 4d-chess-sequential to re-examine at greater sequential depth.
- **Day Shift / Night Shift / Hermes**: Day Shift uses 4d-chess-sequential for deep planning and intent injection on high-value targets (with natural pacing via layer gates). Night Shift cron can run autonomous sequential 4d-chess-sequential passes (with human intent pre-loaded). Hermes can guide or monitor the sequential steps one-by-one for complex sessions.

Cross-reference AGENTS.md: Hard-First Principle, Persistent Looping Discipline, ultrafuzz mandatory before honest-zero claims, operator skills table, skills in .agents/skills/ and hermes/skills/.

## 4D Chess Ingenuity Elevations (Beyond Direct Grego Lift — Sequential Optimized)

- **Explicit 4D State Space**: Formal (lightweight) modeling of the four layers with cross-impact matrices. Makes "why this deep interaction matters" auditable and prioritizable. Processed sequentially with cumulative scoring.
- **Recursive Layer Summarization with Verification Gates**: To scale past 7 layers without context explosion — each deep sub-system summarized with "preserves/violates parent invariant X because Y" + gate check before ascending. Core technique for sequential depth.
- **Economic Layer as First-Class**: Always quantify attacker profit and protocol loss in invariant breaks (ties directly to bounty value and submission impact sizing). Evaluated sequentially after prior layers.
- **Meta-Game Layer (Anticipatory)**: Dedicated sequential reasoning step that models "if this invariant breaks and protocol patches naively, what second-order attack opens?" — pushes beyond static analysis into dynamic adversarial foresight.
- **Signal-from-Failure as Core Sequential Loop**: Dedicated step after each layer (and final synthesis) that treats every false positive, partial break, and harness defect as a pointer. Often leads to the real obscure edge.
- **Intent as Executable Meta-Invariants**: Human-provided protocol purpose is compiled into machine-checkable high-level invariants that guide sequential prioritization, pruning, and refinement.
- **Sequential Depth Scaling via Iterative Refinement Loops**: Achieves 7+ layer depth through repeated self-refinement cycles on focused sub-problems, with summarization and verification gates between iterations. This trades speed for controlled resource usage on rate-limited tiers while preserving (and often increasing) rigor through explicit backtracking and re-evaluation.
- **Hybrid Certification Gate**: No high-severity claim or submission without documented human intent review + 4d depth metric (layers + iterations) + reproducible PoC. Strengthens existing adjudication.

## Anti-Patterns to Avoid

- Treating 4d-chess-sequential as pure autonomous replacement for human judgment (the blog post exists precisely because the creators were "out-hunted" yet still see human edges as decisive).
- Shallow layer traversal or stopping at first invariant break without full sequential cross-layer, economic, and meta-game impact analysis.
- Discarding AI near-misses/false-positives without performing the dedicated sequential signal-mining step after layers.
- Ignoring human intent injection — leads to flagging deliberate design tradeoffs (classic Grego AI limitation without context).
- Running without fresh-context repetition or failure preservation on deep sequential branches/iterations.
- Claiming "thorough" without measuring layers traversed, invariants stress-tested, and sequential iterations performed.
- Using on live mainnet without mirror/fork validation + human oversight (even Grego outputs were human-validated before reporting).
- Attempting any form of parallelism or concurrent tool calls — this variant is deliberately single-threaded to protect rate limits.

## Output & Provenance Standards

Every 4d-chess-sequential run must produce:
- Structured invariant map + 4D impact scores + full Global State log.
- Complete sequential execution trace (layer summaries, branch decisions, refinement iterations, signal-mining outputs).
- Synthesized attack story + reproducible PoC + evidence package (submission-ready).
- Human intent injection log + adjudication notes.
- Meta-metrics: max layers reached, invariants broken/held, sequential iterations performed, signals mined from failures, human-AI division of labor.
- Traceability: git SHAs of target, codegraph output, Crucible version, 4d-chess-sequential skill version, all intermediate summaries and prompts used, human review artifacts.
- Update to lab-notebook and relevant SPEC.md / AGENTS notes if new patterns emerge.

## Quick-Start Example: Heavily Audited Solana DeFi Protocol (Sequential Execution)

1. codegraph explore --target <protocol> --depth 4 (structural foundation).
2. Invoke 4d-chess-sequential with human-provided "protocol intent" (e.g., "Core invariant: user deposits are always withdrawable 1:1 minus fees under normal conditions; oracle updates are trusted but with staleness checks").
3. Phase 0–1: Agent builds layered map and proposes/traces initial invariants sequentially, producing Phase 0 and Phase 1 Summaries.
4. Phase 2: Agent processes 4D layers one by one sequentially:
   - Static Structure: Deepens graph paths, evaluates branches depth-first, produces Static Layer Summary + signal mining.
   - Dynamic/State: Invokes Crucible sequentially on key paths, evaluates state violations, produces Dynamic Layer Summary + signal mining.
   - Economic: Quantifies impacts sequentially, produces Economic Layer Summary + signal mining.
   - Temporal/Meta: Anticipates second-order effects, produces Temporal Layer Summary + final signal mining.
   - Iterative Refinement: One or more focused re-evaluation loops on top branches using accumulated summaries.
5. Human reviews promising break(s) + intent injection confirms it's not a deliberate tradeoff (can happen after key layers or at end).
6. Phase 4: Agent synthesizes full attack story, PoC, and $ impact calc using Global State → submission-reporting.
7. Preserve everything (sequential trace + all summaries); feed new invariant violation back to ultrafuzz property fan-in for regression hunting via targeted follow-up.

This sequential variant was produced via adaptation of the original 4d-chess skill (itself from alpha-miner elevation of Grego AI alpha) to remove all parallelism while preserving full depth, rigor, and NSS integration. It maintains source fidelity while adding explicit rate-limit optimizations, iterative refinement loops, and sequential layer processing. No invention of core mechanisms — rigorous adaptation for controlled execution environments.

**Implementation note**: Added as sequential variant for rate-limited/free-tier use. See .agents/skills/4d-chess-sequential/SKILL.md. Strengthens ultrafuzz/Crucible/codegraph/bounty-loop with 7+ layer multi-dimensional adversarial intelligence via single-threaded iterative deepening and hybrid judgment layer. Trigger: request for second version of 4d-chess without sub-agents, optimized for rate limits.

---

**End of 4D Chess (Sequential) SKILL.md**
