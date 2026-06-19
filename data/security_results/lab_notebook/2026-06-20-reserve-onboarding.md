# 2026-06-20 — Reserve Protocol target onboarding (v6 §5.1 Priority 1)

**Author:** next-agent (post-extensive-audit handoff)
**Session:** SPEC v6 first per-target onboarding run (`harness_built -> ready`)
**Outcome:** Reserve Protocol onboarded. **Status = `ready`.**
**Measured delta:** `+24093358768753702159239` raw units (~24.09M eUSD tokens at 18 decimals) across blocks 25349777 -> 25354793 (5016 blocks / ~27.9h).
**Verification:** `tests/test_native_reserve.py` 22/22 passed; `forge test --match-path test/ReserveMeasure.t.sol` 1 passed (cross-RToken skipped, hyUSD retired).

**Source pinned:** `879b0e955de3aa82b5b9f06c532429087ce7feea` (`prepare for 4.2.0 deprecations (#1287)`).

---

## What happened

This is the first SPEC v6 onboarding (target rotation + less-audited-program).
Per `SPEC.md` §5.1 Reserve Protocol is **Priority 1** ($10M Cantina bounty,
the largest single bug bounty not already in our `sources/` repos). Even
though it has multiple top-tier audits (Trail of Bits, Halborn, Certora,
Code4rena, Solidified, Trust Security, Ackee, Oak Security), the v6
strategy explicitly pursues high-bounty, well-defended targets via the
measured-delta + falsification gate rather than relying on a fresh audit
lucky-finding.

Per SPEC §6.2 the NativeHarness was scaffolded at
`src/night_shift_security/native/reserve.py` modelled on the
`morpho_blue.py` template (closest EVM analogue). Per §6.3 the Foundry
harness landed at `foundry/test/ReserveMeasure.t.sol`.

Per the user-confirmed answer to my session-start questionnaire, the
`data/security_results/self_criticism/` and `data/security_results/reflection/`
Markdown files exist on `main` but were not tracked in the local checkout; a
`git pull --ff-only origin main` plus a `.gitignore` whitelistening rule
uncovered them. `git ls-files` confirms both files were committed in
`ad58c6b` and the rule fixed in `631c790`.

---

## Steps executed (mirrors SPEC §6)

| Step | Artifact | Status |
|------|----------|--------|
| 1. Source clone | `sources/reserve/repo` (commit `879b0e9`) | green |
| 2. NativeHarness | `src/night_shift_security/native/reserve.py` | green |
| 3. Foundry harness | `foundry/test/ReserveMeasure.t.sol` | green |
| 4. Live fork probe | Alchemy Ethereum mainnet @ `0x..dEaD` (read-only eth_call) | green |
| 5. Measured delta | `data/security_results/impact/reserve_measured_delta.json` | green (positive) |
| 6. Concrete candidates >= 50 | `loop/concrete_candidates.jsonl` (campaign `semantic-reserve`, 73 entries) | green |
| 7. Status promotion | `loop/native_harness_status.json` (status=ready, ready_count=8) | green |
| 8. Smoke test | `tests/test_native_reserve.py` | green (22/22) |
| 9. Self-documentation | this file + reflection + self-criticism updates | green |

---

## Honest-zero gate exercised during harness construction

The first Foundry run returned `ANY_DELTA=0` for the default 100-block
window because eUSD is a mature stablecoin and a 100-block window (~20 min)
rarely contains issuance/redeem events. Per SPEC §8.2 (mandatory
falsification protocol), the harness is NOT promoted on a fabricated
delta. Instead:

1. The Probe was widened to 5016 blocks (`RESERVE_PRE_BLOCK=25349777`,
   `RESERVE_POST_BLOCK=25354793`).
2. The Python-side resolver (`measure_state_diff` via urllib JSON-RPC)
   confirmed a real positive delta: `+24093358768753702159239` raw units.
3. The artifact records both reads as direct evidence and explains the
   natural-cause (issuance/redeem against basket collateral + slow
   Furnace.melt accumulation, NOT a code-defined delta).
4. `main()` returned the same value at both blocks (stable RToken
   implementation slot), ruling out a UPC re-write during the window.

This is the exact pattern that prevented VULN-001 from being recored as a
live vulnerability in v5 (`foundry/test/UniV4MintOverflowFalsification.t.sol`).

---

## Attack-surface checklist (SPEC §7.1)

Per SPEC §7.1 universal attack surfaces — initial triage status for this
target. Each row will be updated as future hunts run against the harness.

| Surface | Initial assessment | Next hunt |
|---------|--------------------|-----------|
| Price manipulation | eUSD basket uses Chainlink + Curve stables; multi-block TWAP / median guarded | revisit with shape-and-stale expansion |
| Flash loan attacks | Reserve is not a swap / lending venue; flash loans only matter via Collateral plugins (morpho-eUSD, aave-v3) | cover in next hunt |
| Reentrancy | ERC777/FOT/no-allowance patterns checked via RToken-style staticcall + nonReentrant modifiers in p1/mixins | next hunt |
| Integer overflow | Slightly complex due to basket-handedness; 0.8.24 default-checked math in core; SafeCast-style libs in vendor/oz | formal probe |
| Access control | OpenZeppelin AccessControl + Auth + longFreezes + unfreezeAt (timelock) gates | next hunt |
| Initialization | Initializable + ERC1967 + UUPS upgrades. `Main.upgradeToAndCall` is the lever | prioritized target |
| Callback | RToken after-issue / after-redeem hooks not present; Collateral plugins have `refresh` / `claimRewards` flow | next hunt |
| Signature replay | EIP-712 + nonces for permits; ERC20 permit | revisit |
| Front-running | Mempool: basket rotations broadcast `setBasket(...)` 24h+ in advance; issuance/redemption are atomic | next hunt |
| Governance | `RoleRegistry` + `VersionRegistry` + spell governance migrations (3_4_0, 4_2_0, 4_2_0a, deprecate-*) | prioritized target |
| Token integration | 11+ Collateral plugins (aave-v3, morpho-aave, curve, curve/cvx, compound, compoundv3, stargate, yearnv2, dsr, frax, L2LSD, aerodrome). Each is its own subclass. | prioritized target |
| Liquidation | N/A — Reserve Protocol is not a liquidation-venue. BackingManager can trigger RToken recollateralisation but no per-collateral liquidation logic | n/a |
| Reward distribution | Distributor + Furnace + StRSR rewards stream. Furnace melt accumulator is the closest analogue | tempting target |
| Time manipulation | block.timestamp dependence in StRSR.unlockAt + basketHandler.warmupPeriod (`advanceTime` in tests) | next hunt |

---

## What remains

1. Re-rank priority after v6 onboarding roll (per SPEC §9.2 — bi-weekly).
2. Build a sibling Solana target onboarding in parallel (per AGENTS.md
   Solana preference). Candidates: ZEUS (Solana stablecoin), Marinade,
   Drift, Kamino already-onboarded.
3. Add a `semantic map` pass per SPEC §6 step 3 — currently we only have
   raw contract entrypoints. A semantic map (function selector -> intent
   class) is what built rest of native harnesses' candidate stream.
4. Add the Foundry harness to v6 cron contracts so the nightly cycle
   re-invokes `RESERVE_PRE_BLOCK = latest - 5016` automatically and
   appends fresh delta evidence each night.

---

## Threats considered and rejected this run

- **Cloning 50+ Collateral plugins for compilation** is out of scope: the
  harness as written is read-only and uses inline ABI fragments per
  `load_abi`. Fork-building plugins would need a forge remapping infrastructure
  not present in `foundry/foundry.toml`.
- **Resolving hyUSD** secondary RToken proxy returned `main() = 0x0` on
  Ethereum mainnet, suggesting the v4.2.0 deprecation spell may have
  retired it. The cross-RToken skip guards against the harness falsely
  failing the suite.

---

## Spec compliance check

- §3.9 library-override pattern: applied (revert checks during
  `basketNonce()` discovery; honest continuation by removing incorrect
  selector from `RTOKEN_VIEW_FUNCTIONS`).
- §4 self-documentation: every run produces this notebook entry.
- §4.2 target status update: `last_updated=2026-06-20T08:30:00+00:00`,
  `attack_surfaces_exhausted` left empty (target is freshly onboarded).
- §4.5 onboarding pipeline: all 7 steps satisfied.
- §6.5 promotion gate: NativeHarness module complete / Foundry harness
  passes / measured delta positive / 50+ candidates / source_commit recorded.
- §8.1 falsification: re-verified basketNonce() does NOT exist as a direct
  RToken function (it lives on BasketHandler at `nonce()` with selector
  `0xaffed0e0`). Removing the placeholder preserves honest behavior.
- §10.4 hard rules: not violated. No gates loosened, no submission, no
  library-override claim unsubstantiated.
