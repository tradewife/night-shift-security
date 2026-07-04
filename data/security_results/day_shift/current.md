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

## Night Shift handoff

- Makina campaign is hard-first on primary subsystem; no submission-ready status expected in first rounds.
- Operator action: rotate from Lombard STRAT-S16 closure to Makina (this plan). Cron unchanged (`nss-hipif-chain` 04:00) — does not auto-run Makina; Makina investigation is a day-shift ad-hoc arc.
- On-Chain: NO deployment of these contracts (foundry harness only).

## Carry-forward

- Lombard cross-layer v6.51.19 STRAT-S16 closure (`next.md`) — keep as accepted acceptable-with-gaps.
- Carry-forward items: OnRe human gate, Superform triage follow-up.
- Intel: `data/security_results/intel/latest.md` — augment with `platform sync makina` if/when added.
- Reference: `agglayer-cantina` round-4 runbook for environmental patterns (these are EVM foundry, not Hardhat, but tier-1 reference).
