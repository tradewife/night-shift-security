# Session plan — v6.34 Coinbase Cantina deep-dive sidecar — honest-zero

**Status: closed** (2026-06-29) — v6.34 Coinbase Onchain Bug Bounty (Cantina $5M Tier 0)
deep-dive: Hard-first on most-convoluted intersection of Smart Wallet
+ Spend Permission Manager + SpendRouter + PublicERC6492Validator
+ MagicSpend. 4 carry-forward hypotheses adjudicated without reaching
submission grade; cross-chain replay primitive captured as `documented intent`.

## Summary

Sidecar session. Investigation workspace set up under
`data/security_results/investigations/2026-06-29-v6-34-coinbase-cantina/`.
4 source clones pinned at commits `e7fde11a` / `e0004e63` / `619f20ab` / `988d48c4`.
69-property fan-in across 8 categories A–H; 5 strategy files
STRAT-001..005 targeting 6 hypotheses H1–H6. NativeHarness `coinbase_smart_wallet.py`
+ 19 pytests (all green). Foundry harness `sources/spend-permissions/repo/test/coinbase_propfuzz/`
with **8 suites / 40 tests / 0 failures**, full upstream 201/201 regression clean,
NSS full suite 1002/1002+13-skipped+1-pre-existing KAST failure (unrelated).

### Findings (4 carry-forward hypotheses adjudicated)

| Prop | Adjudication | Evidence |
|---|---|---|
| PROP-CCH-006 cross-chain replay w/ UUPS | `engine_level_honest_zero_with_documented_intent` | CrossChainReplayTest: `getUserOpHashWithoutChainId` identical across chainIds (chainA→99, chainA→8453); 5-selector whitelist includes upgradeToAndCall. Documented design — Coinbase Smart Wallet deploys at same address on all chains via SafeSingletonFactory. |
| PROP-SPM-013 transient _expectedReceiveAmount race | `underspecified_partial_evidence_safe` | SpendTransientRaceTest: receive() reverts correctly when value != expectedReceiveAmount. Transient slot pattern is canonical Solidity-0.8+ defense. Full reentrancy fixture deferred. |
| PROP-SIG-005 RIP-7212 divergence | `engine_level_honest_zero_with_environmental_observable` | Rip7212MockTest: Foundry env shows addr(0x100) staticcall → ok=true, ret.length=0. Library falls through to FCL. abi.decode on 1-byte pads to 0. No exploitable divergence. |
| PROP-RT-007 EIP-7702 persistence check | `underspecified_low_severity` | Router7702Test: SpendRouter constructor rejects 0xef0100-only exact match. Non-7702 23-byte contracts accepted (deploy-time check). No real impact. |

### What did NOT move

- **`submit_ready` unchanged**: still 1 (OnRe H1 from v6.13).
- **No NSS pipeline changes**: 0 changes.
- **No submission drafted**: cross-chain replay primitive is by-design Coinbase
  affordance, well-audited by OpenZeppelin, Certora, Cantina, Code4rena.
- **Phase-4 carry-forward path** is open for PROP-SPM-013 full reentrancy
  fixture if a measured-impact candidate emerges in a future session.

### Artifacts

- Investigation pack: `data/security_results/investigations/2026-06-29-v6-34-coinbase-cantina/`
  - `setup.md`, `property_fanin.md`
  - `strategies/STRAT-{001..005}-*.md` (5 strategy files)
  - `adjudication/PROP-{CCH-006,SPM-013,SIG-005,RT-007}-*.json` (4 adjudication records)
  - `summary.json`
- Lab notebooks: `data/security_results/lab_notebook/2026-06-29-v6-34-coinbase-cantina.md`, `...-phase3.md`
- NativeHarness: `src/night_shift_security/native/coinbase_smart_wallet.py` (19/19 pytests)
- Tests: `tests/test_native_coinbase_smart_wallet.py` (19/19 pytests)
- Target config: `src/night_shift_security/config/targets/coinbase-cantina.json`
- Source manifest: `sources/coinbase/source_manifest.json`
- Foundry tests: 8 files in `sources/spend-permissions/repo/test/coinbase_propfuzz/` (40 totals)
- Source clones: `sources/{coinbase,spend-permissions,webauthn-sol,magicspend}/repo/` (gitignored)

## Submission gate status

| Gate | Status |
|------|--------|
| OnRe H1 (v6.13) | **submit_ready=1** (unchanged) |
| Silo reentrancy (v6.32) | **submission-ready, requires human gate** (unchanged) |
| Veda Token-2022 STRAT-01 (v6.33) | **Honest-zero for current production; live the moment a Token-2022 deposit asset is added to Veda** |
| Coinbase Cantina (v6.34) | **4 carry-forward hypotheses adjudicated honest-zero / documented-intent / underspecified — no submission** |
| Overall `submit_ready` | **1**, unchanged |

---

## Session-37 / v6.32 — Silo Finance reentrancy in defaulting liquidation (closed, requires human gate)

Full validation cycle for PROP-LIQ-SEQ-003-REENTRANCY: reentrancy window in `liquidationCallByDefaulting` where `Actions.repay()` lacks `turnOnReentrancyProtection()` before `beforeAction(REPAY)`. 50k protocol deficit confirmed on mainnet fork. False positive ruled out. Submission package assembled.

### Findings

**PROP-LIQ-SEQ-003-REENTRANCY — Reentrancy window in defaulting liquidation (Critical / Protocol Insolvency)**

Root cause: `Actions.repay()` calls `beforeAction(REPAY)` without enabling reentrancy protection. `liquidationCallByDefaulting` turns the guard off before `_repayDebtByDefaulting()`. A malicious hook reenters `ISilo.repay()` during this window, reducing `totalAssets[Debt]` twice (hook + outer liquidation) while collateral is seized once.

| Test | Status | Evidence |
|------|--------|----------|
| `test_exists` | PASS | Reentrancy window fires |
| `test_deficitExists` | PASS | Deficit = 50,000 tokens = hook repayment |
| `test_maxDeficit` | PASS | 116,645 deficit (33% of 350k debt) |
| `test_fork_exploit_exists` | PASS | 50k deficit on mainnet fork (block 22800000) |
| `test_fork_clean_noExploit` | PASS | No deficit without exploit on fork |
| `test_cleanLiquidation_balanced` | PASS | Protocol balanced when no REPAY hook |
| `test_edge_afterActionFires` | PASS | afterAction(REPAY) also fires without guard |
| `test_edge_lenderDepositsSafe` | PASS | Lender deposits preserved |
| `test_harnessNotArtifact` | PASS | IRM bypass has no effect on exploit |

**v6.32 submission-ready, requires human gate.**
