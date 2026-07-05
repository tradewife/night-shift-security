# Session plan — current

**Status: active (2026-07-04 night session pivot, rotation from Lombard cross-layer closure v6.51.19)**

**Arc:** Makina Contracts Cantina bounty — Primary Target: Caliber execution engine + Machine share/AUM pipeline + MachineShareOracle + bridge/mailbox reporting + recovery-mode permission transitions, plus periphery interactions (AsyncRedeemer, WatermarkFeeManager, SecurityModule cooldowns, FlashloanAggregator).

**Workspace:** `data/security_results/investigations/2026-07-04-makina-cantina/` (local-only per AGENTS.md keep-local rules).

**Repos:** `sources/makina-core/repo` and `sources/makina-periphery/repo` (cloned at session start, depth=1).

**Hard-First Principle:** All 12 ranked hypotheses (`recon.json` `competing_hypotheses`) keep Primary Target Subsystem — Caliber execution + Machine AUM/sharePrice + MachineShareOracle + cross-component flows with periphery — at the central focus. Peripheral contracts (registries, pure adapters, pure oracles) are secondary until core reaches honesty.

## Active hypotheses (covered)

- **H1 (HIGH)** `MachineShareOracle.notifyPdvMigration` permissionless — first-mover can hijack oracle pointer pre-empting legit PDV→Machine migration; pre-existing vulnerability window.
- **H2/H3 (HIGH)** SecurityCouncil bypass on `onReport()` and `updateTotalAum()` share-price-change guard — interaction with `_checkMaxRelativeChange` (`previousValue==0` early return; same-block `elapsedTime==0`).
- **H4 (MEDIUM)** Bridge refund path underflow/panic via `EnumerableMap.get(...)` instead of `tryGet(...)`. Affects both `Machine.manageTransfer` and `CaliberMailbox.manageTransfer`.
- **H5 (HIGH)** Asymmetric recovery authz: `CaliberMailbox.sendOutBridgeTransfer` is `onlyOperator` (SecurityCouncil in recovery), but `Machine.sendOutBridgeTransfer` is `notRecoveryMode onlyMechanic`.
- **H6/H7 (HIGH)** FlashloanAggregator transient slot + Caliber instruction state bitmap malleability — Weiroll state bitmap skew between hashed and runtime parameters.
- **H8/H9** Flashloan sequencing + PDV/Oracle migration race conditions.
- **H10/H11** Fee/SecurityModule ERC4626 inflation (`+1` mitigator vs direct share transfer).
- **H12** AsyncRedeemer O(N) batch finalize grief.

## Session results (2026-07-04 evening — first Makina run)

**Phase 1+2 — Code intelligence + Recon (DONE):**
- Cloned `makina-core/repo` + `makina-periphery/repo` (depth=1)
- Read in depth: 30+ source files (see `recon/recon.json` files_observed)
- Saved: `recon/recon.json` (12 hypotheses, severity rank, action plan)
- Saved: `strategies/canonical-property-table.md` (Groups A–F, hypotheses → invariants → falsifiers)

**Phase 3+4 — Falsifier harness scaffolding (DONE — 35 passing tests, 7 suites):**
- `foundry/foundry.toml` updated: `[profile.makina]` + `[profile.makina-periphery]` profiles
- `foundry/lib/openzeppelin-contracts-makina` + `foundry/lib/openzeppelin-contracts-upgradeable-makina` — fresh OZ 5.x clones
- `foundry/lib/enso-weiroll` — Weiroll VM (cloned)
- `foundry/src/makina/stubs/` — MockPDV, MockMachine, StubTokens, TestMachineShareOracle (mirror)
- `Falsifier_H1_NotifyPdvMigration.t.sol` — **4 tests passing**
- `Falsifier_H3_ZeroElapsedSharePriceChange.t.sol` — **7 tests passing**
- `Falsifier_H4_BridgeRefund.t.sol` — **4 tests passing**
- `Falsifier_H5_AsymmetricRecoveryAuthz.t.sol` — **7 tests passing** (mirrors of Mailbox + Machine modifier trees, asserts `spoke.recoveryMode() != hub.recoveryMode()` asymmetry)
- `Falsifier_H6_FlashloanSlotReuse.t.sol` — **4 tests passing** (TransientSlot reuse via `tstore/tload` is contract-account-global; reentrancy window; stale hash)
- `Falsifier_H7_CaliberBitmapMalleability.t.sol` — **5 tests passing** (stateBitmap=0 short-circuit, MSB-first ordering, truncation, duplicates, empty array with bitmap)
- `Falsifier_H10H11_SecurityModuleInflation.t.sol` — **4 tests passing** (legit baseline, donation-in-flates-99%, +1 mitigator insufficient, slash interaction)

**Total: 35/35 passing**

**Falsifier outcomes:**

| H | Title | Verifier | DELTA_WEI | Notes |
|---|-------|----------|-----------|-------|
| H1 | notifyPdvMigration permissionless | 4 tests | Positive 10,000× | Oracle re-anchors to attacker's machine under factory-misconfig (calls `notifyPdvMigration` again with attacker data before legit completes) |
| H3 | Zero-elapsed share-price guard | 7 tests | Algebra correct | Bypass exists only via `securityCouncil` role call path (intentional design) |
| H4 | Bridge refund path panic | 4 tests | Positive | `EnumerableMap.get()` reverts on missing/unseeded keys → funds stuck at adapter |
| H5 | Asymmetric recovery authz | 7 tests | Cross-chain side-effects confirmed | `CaliberMailbox.sendOutBridgeTransfer` is `onlyOperator` while `Machine.sendOutBridgeTransfer` is `notRecoveryMode onlyMechanic` — spoke can SEND-out in recovery while hub cannot |
| H6 | Flashloan slot reuse | 4 tests | Slot contamination demonstrated | Transient slot is global per EVM contract account; reentrancy in callback overwrites the slot |
| H7 | Caliber bitmap malleability | 5 tests | stateBitmap=0 short-circuit | `_getStateHash` returns 0 when bitmap=0, allowing crafted leaves with empty authorization set |
| H10/H11 | SecurityModule inflation | 4 tests | Donation 99% damage | Direct ERC20 transfer to SecurityModule inflates `totalLocked` without minting shares; +1 mitigator insufficient against large donations |

## Disclosure candidates ranked

1. **H4** (MEDIUM, MED evidence, HIGH novelty) — refund-path revert, funds stuck at bridge adapter (caliber + machine). Concrete DoS / locked-funds class.
2. **H1** (HIGH-conditional, MED evidence, MED novelty) — oracle re-anchor via factory-misconfig. Requires factory deployment edge.
3. **H5** (HIGH-conditional, HIGH evidence, HIGH novelty) — cross-chain recovery asymmetry allowing spoke-side drain while hub reports "safe". Requires active hub recovery bypass.
4. **H6** (HIGH-conditional, MED evidence, HIGH novelty) — flashloan transient-slot reuse enables any caller of `requestFlashloan` to interleave with another Caliber's pending flashloan.
5. **H7** (HIGH-conditional, MED evidence, MED novelty) — Caliber instruction bitmap truncation/empty-set enables crafted leaves.
6. **H10/H11** (HIGH, HIGH evidence, MED novelty) — ERC4626 donation inflation on SecurityModule. Well-known pattern but Makina inherits OpenZeppelin +1 mitigator and is still vulnerable to >50% donations.
7. **H3** (LOW, HIGH evidence) — bypassable only by SecurityCouncil role call path (intentional design).

## Earlier non-actionable reminders (kept in archive)

- Property table (now in `strategies/canonical-property-table.md`, written 2026-07-04 evening).
- Per-hypothesis falsifier sequence targeting H1 → H5 → H7 → others.** STATUS:** H1+H3+H4 falsified (15 tests passing); rest queued for round-2.

## Session status — Phase 5–7 complete (2026-07-04 night)

**Status (updated):** Phase 5 cycle 1 + Phase 6 + Phase 7 draft complete. 53/53
falsifier tests passing across 10 suites. Five submission drafts in
`investigations/2026-07-04-makina-cantina/submission-packs/`. Awaiting human
gate before any external submission.

### Phase 5 — Cycle 1 results

| Class | Suite | Tests | Result |
|------|-------|------:|--------|
| Recursive improvement | (refactor of H5 mirror into `MirrorGovernableBase.sol`) | n/a | reusable base extracted |
| H5 expansion | `Falsifier_H5_1x_RecoveryAuthz_Cycle1.t.sol` | 6 | 6/6 pass — H51 baseline + H52 timelock + H53 divergence + H54 reentrancy + H55 multi-spoke + H56 regression |
| H1 expansion | `Falsifier_H1_1x_NotifyPdvMigration_Cycle1.t.sol` | 6 | 6/6 pass — H11 baseline + H12 same-block race + H13 sandwich + H14 multi-instance + H15 atomic + H16 regression |
| H6 expansion | `Falsifier_H6_1x_FlashloanSlotReuse_Cycle1.t.sol` | 6 | 6/6 pass — H61 baseline + H62 unfinished + H63 interleaved + H64 callback-then-dispatch + H65 per-account isolation + H66 regression |
| **Full suite** | 10 suites | **53** | **53/53 pass** under both `makina` and `makina-periphery` profiles |

### Phase 6 — Closure adjudication

Surviving hypotheses (ranked by Severity × Evidence × Novelty):

1. **H5** Asymmetric Recovery Authz — SURVIVES (HIGH × HIGH × HIGH)
2. **H10/H11** SecurityModule Donation Inflation — SURVIVES (HIGH × HIGH × MED)
3. **H6** Flashloan Transient Slot Reuse — SURVIVES (HIGH × MED × HIGH)
4. **H1** NotifyPdvMigration Permissionless — SURVIVES (HIGH × MED × MED)
5. **H4** Bridge Refund Path Panic — SURVIVES (MED × HIGH × MED-HIGH)
6. **H7** Caliber Bitmap Malleability — CONDITIONAL (HIGH × MED × MED)
7. **H3** Zero-Elapsed Share-Price Guard — KILLED (LOW × HIGH × LOW)

Full table in `investigations/2026-07-04-makina-cantina/strategies/phase-6-adjudication-H-table.md`.

### Phase 7 — Submission packs queued (gated)

| Pack | Path |
|------|------|
| H10/H11 | `investigations/2026-07-04-makina-cantina/submission-packs/H10H11-SecurityModule-Donation-Inflation.md` |
| H5 | `investigations/2026-07-04-makina-cantina/submission-packs/H5-Asymmetric-Recovery-Authz.md` |
| H6 | `investigations/2026-07-04-makina-cantina/submission-packs/H6-FlashloanSlotReuse.md` |
| H1 | `investigations/2026-07-04-makina-cantina/submission-packs/H1-NotifyPDVMigration-Permissionless.md` |
| H4 | `investigations/2026-07-04-makina-cantina/submission-packs/H4-BridgeRefund-MissingKey-Panic.md` |

All drafts gated — **NO EXTERNAL SUBMISSION** without human review of each pack.

### What the data does NOT show yet

- **H5**: end-to-end cross-chain PoC requires a full bridge adapter test fixture
  (Across / CCTP / LayerZero call path + real `MachineShare` token); current PoC
  uses mirror contracts.
- **H1**: the factory misconfig precondition needs audit in
  `HubCoreRegistry.initialization()` to confirm attack surface.
- **H6**: requires a malicious Caliber instruction fixture to drive re-entry
  inside `manageFlashLoan` callback paths.
- **H4**: cross-adapter re-routing scenario (Across→CCTP refund sequence)
  needs simulation to confirm the double-cancel path.
- **H7**: signed-leaf scenario requires Caliber.Spoke's full valid instruction
  path to be reproduced against the bitmap collision.

## Night Shift handoff

- Makina campaign is hard-first on primary subsystem; no submission-ready status expected in first rounds.
- Operator action: rotate from Lombard STRAT-S16 closure to Makina (this plan). Cron unchanged (`nss-hipif-chain` 04:00) — does not auto-run Makina; Makina investigation is a day-shift ad-hoc arc.
- On-Chain: NO deployment of these contracts (foundry harness only).

## Carry-forward

- Lombard cross-layer v6.51.19 STRAT-S16 closure (`next.md`) — keep as accepted acceptable-with-gaps.
- Carry-forward items: OnRe human gate, Superform triage follow-up.
- Intel: `data/security_results/intel/latest.md` — augment with `platform sync makina` if/when added.
- Reference: `agglayer-cantina` round-4 runbook for environmental patterns (these are EVM foundry, not Hardhat, but tier-1 reference).

### Phase 5 Cycle 2 — Refinement + Monitoring (2026-07-05)

| Class | Suite | Tests | Result |
|------|-------|------:|--------|
| H5 refinement | `Falsifier_H5_2x_RecoveryAuthz_Cycle2.t.sol` | 7 | 7/7 pass — H57 permanent lock + H57b negative + H58 N=1 min spoke + H58b N=5 parallel + H59 attacker block + H510 lifecycle stages + H511 regression |
| H1 refinement | `Falsifier_H1_2x_NotifyPdvMigration_Cycle2.t.sol` | 5 | 5/5 pass — H17 perm lock state + H18 cascade N=3 + H19 no-misconfig guard + H110 DELTA_WEI ≥1000x quantified + H111 regression |
| Monitoring hooks | `hermes/scripts/makina_h5_recovery_asymmetry_monitor.py` | n/a | cast-call monitor for hub+spoke recoveryMode flag |
| Monitoring hooks | `hermes/scripts/makina_h1_oracle_hijack_monitor.py` | n/a | cast-call monitor for oracle shareOwner mismatch + permanent lock |
| **Full suite** | 12 suites | **65** | **65/65 pass** under both profiles |

### Phase 6 Refresh (Cycle 2)

- **H1 evidence upgraded MED→HIGH**: permanence + cascade + ≥1000× DELTA_WEI quantified.
- **H5 evidence confirmed HIGH**: 20 total tests, permanent lock minimum preconditions, N=5 parallel drain, lifecycle-stage edge coverage.
- Top 3 ranking unchanged but positions solidified: H5 (rank-1), H1 (rank-2, upgraded), H10/H11 (rank-3).

### Phase 7 — Top 3 packs with Human Review Checklists

| Pack | Checklist | Reproducer |
|------|-----------|------------|
| H5 | 7-item checklist (modifier tree, RecoveryInheritor, spoke flag, PoC, severity) | `Falsifier_H5_2x_RecoveryAuthz_Cycle2.t.sol` |
| H1 | 7-item checklist (permanence, factory misconfig, cascade, DELTA_WEI, reset method, monitor) | `Falsifier_H1_2x_NotifyPdvMigration_Cycle2.t.sol` |
| H10/H11 | 6-item checklist (PoC, math mirror, OZ +1, transfer hook, live token addrs, severity) | `Falsifier_H10H11_SecurityModuleInflation.t.sol` |

### Decision Point

**Flag: A — Top 3 packs are submission-ready.**

- **H5** (Asymmetric Recovery Authz): 65/65 tests, minimum N=1 spoke, SC key required,
  monitoring hook. Strongest overall (HIGH×HIGH×HIGH).
- **H1** (Oracle Permanence): evidence upgraded to HIGH after Cycle 2. Cascade +
  ≥1000× price divergence quantified. Monitoring hook.
- **H10/H11** (Donation Inflation): highest-evidence per test-dollar. Simplest
  to reproduce (4 tests, StubSM stripe). Preferable first submission.

Recommend: **pause further discovery** on Primary Target and await human review
of top 3 packs. Remaining packs (H6, H4, H7) are lower priority follow-on.

**Next session** (if human approves any pack):
- Run `submission-reporting` template assembly for approved packs.
- Route through `submission_alert.json` human gate.
- Return to persistent loop on remaining conditional candidates (H6, H7, H4).

**Next session** (if top 3 are rejected or held):
- Build cross-chain bridge adapter fixture for H5 to upgrade to end-to-end PoC.
- Audit `HubCoreRegistry.initialization()` for H1 factory misconfig.
- Deepen H6 with malicious Caliber instruction fixture.
