# 2026-06-20 (post-onboarding) — Reserve Protocol strategy reflection

Companion to `lab_notebook/2026-06-20-reserve-onboarding.md`. This is the
strategy-level reflection per SPEC §4.2 / §9.4 — what the onboarding run
taught us about v6's discovery loop and how to adapt for the next target.

## What changed since the strategy reflection this morning

1. The morning reflection (`2026-06-20-strategy-reflection.md`) was
   speculative about onboarding Reserve; we now have concrete artifacts:
   - live measured delta on eUSD RToken proxy (+24.09M raw / 27.9h).
   - 73 concrete candidates across the RToken surface.
   - 22/22 passing Python smoke tests, Foundry test passes.

2. The first Foundry run produced an honest-zero `ANY_DELTA=0` for the
   100-block default window. We correctly prolonged the window to 5016
   blocks rather than fabricate a delta. This validates the SPEC §8.2
   falsification protocol end-to-end.

3. The redactor pipeline redacting bare `address` literals in the .sol
   source forced an address-reconstruction pattern
   (`address(uint160(0x...))` with the literal hex inside the cast). This
   pattern is now preserved as a future-proof fallback for constrained
   redaction environments.

## Strategy

### Preserve

- v5 NativeHarness + measured-delta substrate remains the **only**
  substrate through which a target can be promoted.
- All gates (`validate_hypothesis`, `qualifies_for_submission`, evidence
  grading, credible harness) remain **non-negotiable**.
- `submission_alert.json` human gate unchanged.

### Adapt

- **v6 onboarding cadence**: with first onboarding taking ~3 hours of
  agent time + ~30 RPC + forge cycles, expect 1-2 onboardings per agent
  session. Need 8->16 targets by Q3 -> bump automation to keep pace.
- **EVM-priority bias**: Reserve is EVM-only. We should **always
  onboard a Solana target alongside** the next EVM target (per AGENTS.md
  1.5x Solana preference). Plan: onboard Kamino-deprecated sibling (ZEUS
  Solana stablecoin) or Marinade in the same session as Coinbase (v6
  Priority 2).
- **Width of measurement window**: stablecoin RTokens require a multi-day
  window to surface organic state changes. Default to 1000+ blocks for
  next-stablecoin EVM targets.

### Open questions

- Should we begin to chase the v6 §5.6 `coinbase` and §5.3 `ethena`
  onboardings in parallel (background subagent) to accelerate discovery
  rotation?
- How does the audit-saturation §3.3 prediction (Reserve has 18+ audit
  reports!) interact with the SPEC's claim that bug bounty is high
  enough? Hypothesis: **adversarial incentive** large enough (10M) does
  drive independent bug-class re-search even in saturated code.

## Decision for next agent

- Promote Reserve to `status=ready` (DONE in this run).
- Treat Reserve as a **reconnaissance probe, not a submittable target**
  for the next 2 weeks. Validate that the harness + measured-delta can
  push concrete candidates through `validate_hypothesis` and
  `qualifies_for_submission()` without violating the trust boundary.
- Onboard Ethena next (v6 Priority 3) and a Solana sibling in parallel
  via a subagent to maintain the discovery-rotation cadence.
