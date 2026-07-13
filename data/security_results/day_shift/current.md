# Session plan — current

**Status: active (2026-07-13). Ammalgam DLEX Cantina bounty — 4d-chess-sequential v2 session closed honest-zero with extended provenance. All invariant surfaces tested: accounting identity validated, P10/P11 liquidation fuzz passed, P3 inconsistency bounded as unreachable. submit_ready unchanged (0).**

## Ammalgam 4d-chess-sequential v2 — closeout (2026-07-13)

### Scope

- Target: Ammalgam DLEX Cantina bounty (b5e376ee-...). Protocol: concentrated-liquidity AMM with leveraged/perpetual positions, saturation-based liquidation, and two-token accounting.
- Skill: 4d-chess-sequential (sequential deep-invariant analysis optimized for rate-limited environments).
- Contracts analyzed: AmmalgamPair, TokenController, ERC20Base, ERC20Hooks, HookRegistry, PartialLiquidations, Saturation, Liquidation, Convert, Validation (validateSolvency, checkLtv, checkLeverage, calcDebtAndCollateral), TWAP, InterestLibrary, FixedPoint128/96, OracleLibrary, constants.
- FOUNDRY_PROFILE=ammalgam for isolated builds (solc 0.8.28).

### Key results

- **Fresh-pair fork harness**: Deployed new Ammalgam pair from live mainnet factory (0x1a411b0f...) with MockERC20 tokens. Beacon at 0xf6EF8FEbBa67e70640D5f293c8fe3ea35906990a, pairImpl at 0x1b72e08c51e00660e78378158c406f3Bfc906b67.
- **Canonical accounting identity**: Derived `balX + borrowX - depositX - reserveX == 0` from TokenController.getNetBalances. Tested through 3 iterations of interest-accrual basis diagnosis; all DIFFs traced to harness artifacts (getReserves vs totalAssetsAndShares timing after vm.warp), not protocol bugs.
- **P10LiquidationFuzz.t.sol**: Multi-actor randomized sequence (mint, deposit, borrowX/Y, swap, warp, liquidations) — 250+ lines.
- **P11LiquidationScenario.t.sol**: Deterministic correctly-funded liquidation with all 3 types (hard, saturation, leverage) — 200+ lines.
- **P3 inconsistency analysis**: `ltvOk=true, levOk=false` counterexample from prior session traced through call graph. AND-gated in all caller paths (validateSolvency → validateLTVAndLeverage). Bounded to degenerate ticks (minTick=maxTick=0) and BOR_Y ~4.5e55 — orders of magnitude beyond live pair capacity.

### Verdict

**Extended provenance: honest-zero on all tested invariant surfaces.** No submit-ready bug identified. submit_ready unchanged (0).

### Artifacts (local per AGENTS.md push policy)

- `foundry/ammalgam/test/P10LiquidationFuzz.t.sol`
- `foundry/ammalgam/test/P11LiquidationScenario.t.sol`
- `foundry/ammalgam/test/ForkCheck.t.sol`
- `data/security_results/lab_notebook/2026-07-13-ammalgam-4dchess-session2.md`

### Next

Transition to next target per SPEC §4.4 (MarginFi v2 or similar higher-signal target).
