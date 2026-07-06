# Session plan — next

**Status: queued**

## v6.53 Euler v2 EVC cross-vault contagion (in-progress, session-3 carry-forward)

- **Verdict at session-2 close:** FoT accounting desync PoC confirmed (6 tests). Corpus correlation completed (9 findings). EPO all-oracle staleness confirmed fixed. Fork-verified PoC needed for submission decision.
- **submit_ready: unchanged (0)** — not a candidate promotion yet.
- **Session-2 artifacts (kept-local):** `data/security_results/investigations/2026-07-06-euler-v2-evc-cross-vault/` — `corpus_correlation_session2.md`, PROP-EV2-008 appended, INV-EV2-010 appended, `foundry/src/euler_v2/harness/EulerV2Harness.t.sol` (6 PASS).
- **Source-of-truth bounty:** https://cantina.xyz/bounties/4d285eee-602e-440a-845e-25e155cec26a
- **Closeout criterion:** 1 fork-verified HIGH+ candidate or diminishing returns on Primary Target Subsystem.

### Session-3 blocking items (priority order)

1. **EPO forge build**: Fix pendle relative-import symlink issues to unblock forge build + slither run.
2. **Slither EPO**: Run slither on EPO now that submodules are bootstrapped.
3. **PROP-EV2-008 fork test**: Deploy fee-charging ERC4626 mock vault + mainnet EulerRouter fork test.
4. **Full EVC batch fork harness**: Import EVault modules + EVC + live `verifiedArray()` perspective vault addresses for H1/H3/H5.
5. **Pull `verifiedArray()` vault addresses**: Resolve from Cantina docs or on-chain EVC mainnet.

### FoT PoC status

- **Confirmed**: 100 bps divergence per deposit, share price masking, cross-vault overvaluation.
- **Gap**: Need to demonstrate exploitability via cross-vault liquidation path (EVC batch defenses may block). Fork test required.
- **Next**: If EVC batch indeed blocks the liquidation path, document as honest-zero with confidence and pivot to PROP-EV2-008.

## LI.FI Diamond routing (closed scope-blocked, v6.51.23)

- **Verdict:** no submission-ready finding; **submit_ready: false**
- **Result:** 23/23 tests passing at 10K fuzz runs across 7 Foundry harnesses
- **EXECUTOR-ALLOWLIST-BYPASS:** Confirmed technical vulnerability (medium-high) but scope-blocked by Self-Crafted Calldata Risks exclusion — LI.FI backend/SDK never targets Executor for approvals
- **PROP-LIFI-C1:** Owner-only, excluded by Centralization By Design
- **Value conservation:** Honest-zero across all tested scenarios
- **Do not reopen** without bounty scope changes or new LI.FI contract versions

## Polymarket Cantina (closed honest-zero, v6.51.21)

- **Verdict:** no submission-ready finding; **submit_ready: false**
- **Result:** 51/51 tests passing, 14 hypotheses tested, all disproven or Low-Medium severity
- **Only finding:** overflow DoS at `Trading.sol:654` — real but marginal (operator controls matching)
- **Do not reopen** without new bounty scope additions or significant new attack surface

## Lombard cross-layer (closed acceptable-with-gaps, v6.51.19)

- **Verdict:** no submission-ready finding; **submit_ready: false**
- **Strands closed:** 3 substrate-confirmed honest-zeros (R1 rollback, R2 PDA collision, R3 Rust probes) + 1 round-level engineering_blocker
- **PROP-EVM-MBOX-005 deferred:** cross-layer refund — requires Hardhat fork, not available
- **Do not reopen** without new bounty scope additions, program versions, or explicit Hardhat fork substrate

## Symbiotic Cantina (closed honest-zero, v6.51.22)

- **Verdict:** no submission-ready finding; **submit_ready: false**
- **Result:** 50+ contracts analyzed across 5 repos, 6 audits cross-checked, all fuzz harnesses pass
- **BurnerRouter no-access-control:** confirmed via 9 PoC tests but no net profit path (credits separated by receiver, attacker can only launder own tokens)
- **Do not reopen** without new scope additions or significant new attack surface not covered by 6 audits

## Priority candidates

1. **Drift Token-2022 spot path testing** local validator, fee mint collateral vs recorded
2. **next Cantina/Immunefi slug** (operator choice)
3. **Lombard Crucible** if mailbox + bridge instructions get new action coverage
4. **Midas Stream B** validator repro mint_request reject_mint_request

## Carry-forward

- Resolve OnRe human-gate (submit_ready queue)
- Superform submitted 2026-07-01 await triage
- Weekly: platform sync all
- `delivered_vs_promised.json` and round-level engineering_blocker reclassification: now standard practice in all STRAT specs

## Night Shift handoff

- Do not promote candidates without human gate
- Lombard closed acceptable-with-gaps — deprioritize on cron
- Prefer Crucible for Solana invariant fuzz when feasible
- Intel: data/security_results/intel/latest.md

## Blocks

- [ ] Kate: choose next bounty / program for current.md
- [ ] Human-review outstanding submissions (OnRe)
- [ ] Hardhat fork env needed for PROP-EVM-MBOX-005

## Makina carry-over (post-2026-07-05 hard-rule halt)

- **submit_ready: false.** Decision: NO invocation of `/submission-reporting` without fork-verified PoC against deployed bytecode.
- `submission-packs/H5`, `H1`, `H10H11` remain gated on human review (per `current.md` Pre-Human-Gate Screening).
- Fork-probe infrastructure is **durable**: `hermes/scripts/makina_fork_probe_verify.py` + `foundry/src/makina/tests/ForkProbe_H1_H21.t.sol` (3 tests passing) reproduced against `ALCHEMY_API_KEY` at block 25463221.

### Re-queue triggers (any one reopens Makina)

1. New audit-completion event from Ottersec / Cantina / Trail-of-Bits / Spearbit on the same scope.
2. Makina team announcement of v1.3 release.
3. Public bug disclosure from a third-party researcher.

### Deferred attack-surface hypotheses (operator's pick when re-queued)

- **H22 Deep read of `DirectDepositor`:** Even though direct depositor is non-nonReentrant, the real Machines use WETH/USDC tokens (no hooks). Try to instrument a Foundry fork with a malicious mock token to demonstrate H22 does not actually surface in production.
- **H23 Stale-AUM sandwich:** Explicitly OoS by Cantina page. The remaining concrete move is to document the OoS finding text + keep the falsifier as a forensic artifact only.
- **H24 cross-adapter goroutine:** Out-of-scope-adjacent. Build the round-trip fixture between AcrossV3 and CCTPV2 to confirm the "wrong bridge data hash on receiver side" OoS by example.
- **H25 Production-state differential scan:** Need paid Alchemy tier for full-archive `eth_getLogs` with >10-block window — top-up prerequisites on the operator side.

### Outstanding artifacts (keep-local)

- `data/security_results/investigations/2026-07-04-makina-cantina/HUNTING-ARC-HANDOFF.md`
- `data/security_results/lab_notebook/2026-07-05-session-makina-fork-probe.md`
