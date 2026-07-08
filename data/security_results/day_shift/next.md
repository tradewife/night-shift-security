# Session plan — next

**Status: queued**

## Reserve Protocol Cantina — CLOSED HONEST-ZERO (v6.55)

- **Verdict at close:** Full skill chain (operator-recon → codegraph-x-ray → vault-pattern-match → ultrafuzz-discovery) + live mainnet fork escalation. **10/10 tests PASS** (6 unit + 4 fork). Engine-level honest-zero.
- **Live eUSD mainnet fork results:** 8 components resolved, 10 registered assets enumerated (none upgradeable), claimRewards delegatecall path confirmed executable, basketsNeeded > 0.
- **Only weakness:** RES-UFUZZ-004 (refreshBasket missing globalNonReentrant guard) — design weakness, not independently exploitable.
- **submit_ready: unchanged (0)**
- **Key artifacts (kept-local):** `data/security_results/investigations/2026-07-08-reserve-cantina/` (recon, vault-pattern-match, ultrafuzz, fork-findings), `foundry_reserve_test/ForkReserve.t.sol`.
- **Deferred vectors (lower probability):** oracle manipulation test for compromiseBasketsNeeded, cross-component race with guard gap.
- **Do not reopen** without new scope additions or significant new attack surface.

## Metric OMM Sherlock #1279 — CLOSED HONEST-ZERO (v6.54)

- **Verdict at close:** 10 strategies, 29 test variants, 437 tests pass across 3 crates (`metric-core` 213, `metric-periphery` 149, `smart-contracts-poc` 75). 9 honest-zero + 1 positive signal (L-29 `register()` clears admin blacklist).
- **L-29 bug confirmed but NOT submitted.** Reasons:
  1. The May collaborative audit (linked in contest README, `2026-07-06_Metric-Collaborative_Audit_Report.pdf` p.99) lists the same code as **L-29 [ACKNOWLEDGED, won't fix]**, source `sherlock-audit/2026-05-metric-may-22nd/issues/124`.
  2. Sherlock guideline VII.16 invalidates issues from prior audits (linked in the contest README) marked ACK/unfixed.
  3. Contest README declares `Oracle ADMIN_ROLE` **trusted** for blacklist/integrators/factories/registration fee/withdrawEth.
  4. Prior audit's own impact assessment: "Operational control only — no funds are at risk." No isolated loss-of-funds path.
- **submit_ready: unchanged (0)**
- **Key artifacts (kept-local):** `data/security_results/investigations/2026-07-07-metric-omm-sherlock-1279/` with `findings_report.md` (H1-H6 disposition table), `findings/L-29-blacklist-bypass.md` (positive signal, intentionally withheld), `2026-07-metric-tradewife/smart-contracts-poc/test/StratRegisterBlacklist.t.sol` (3 PoC tests, all PASS), `dup_analysis.md`, prior-audit reference PDFs.
- **Caveat:** public fork snapshot is commit `2e4e866`; contest README pins private commits `7b9ab56`/`d210a84`/`056c204` (inaccessible). Disposition of all 10 hypotheses is robust to this delta.
- **Do not reopen** without exact-audit-tree access, new in-flight commits, or operator-validated candidate. Filing a known-ACK'd issue risks a public-record invalid.

## Euler v2 EVC cross-vault — SCOPE-BLOCKED (v6.53.1)

- **Verdict at close:** FoT accounting desync confirmed technically (11 tests, 7 local + 4 fork) but **out of scope** per Cantina "weird tokens" exclusion. Fork-verified propagates through real EulerRouter on mainnet.
- **submit_ready: unchanged (0)**
- **Key artifacts:** `EulerV2Harness.t.sol` (7 PASS — cross-vault borrow exploit confirmed), `EulerV2ForkVerify.t.sol` (4 PASS — EulerRouter inflation, bad debt, compounding divergence)
- **Do not reopen** without scope changes or discovery of a production FoT vault configured as Euler known vault
- Remaining items (EPO slither, PROP-EV2-008 fork test, full EVC batch fork harness) are lower signal given scope constraints

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
5. **Metric OMM H-1 router-callback-allowance drain** (collaborative report H-1) — only worth following if exact-audit-tree access is granted and H-1 is not in the ACK list of a more recent contest snapshot

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
- [ ] Exact-audit-tree access for Metric OMM (`7b9ab56`/`d210a84`/`056c204`) if any operator wants to re-open L-29 disposition

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
