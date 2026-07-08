# Session plan — current

**Status: closed honest-zero (2026-07-08). Reserve Protocol Cantina v6.55 session complete — full skill chain + fork escalation. Pivot needed.**

## Active arc: Reserve Protocol Cantina ($10M CRITICAL, v6.55)

**Campaign:** Cantina bounty — full skill chain: operator-recon → codegraph-x-ray → vault-pattern-match → ultrafuzz-discovery (unit + fork)
**Live target:** eUSD mainnet RToken at `0xA0d69E286F7f4C9cA3C231a19377bA77d83aDd27`
**Workspace (kept-local, gitignored):** `data/security_results/investigations/2026-07-08-reserve-cantina/`

### Results — 10/10 tests PASS (6 unit + 4 fork), engine-level honest-zero

**Unit phase (6/6 PASS):** `ReserveGuardGapProbe.t.sol`

| Test | Result |
|------|--------|
| test_refreshBasket_during_guarded_operation | PASS — guard gap confirmed: refreshBasket callable while lock held |
| test_refreshBasket_not_guarded | PASS — confirmed no guard on refreshBasket path |
| test_globalNonReentrant_is_guarded | PASS — globalNonReentrant guard works on other p1 functions |
| test_multiple_refreshBasket_during_lock | PASS — multiple refreshBasket calls succeed during lock |
| test_governance_basket_switch_during_lock | PASS — governance can change basket during lock |
| test_disableBasket_not_guarded | PASS — disableBasket also not guarded |

**Fork phase (4/4 PASS on live eUSD mainnet):**

| Test | Result |
|------|--------|
| test_component_discovery | PASS — 8 components resolved from Main proxy `0x7697aE...` |
| test_registered_assets_enumeration | PASS — 10 ERC20s enumerated; none are upgradeable proxies |
| test_claimRewards_storage_collision_probe | PASS — delegatecall executable; tradesOpen invariant held (0→0); codehash unchanged |
| test_compromise_baskets_needed_probe | PASS — basketsNeeded queryable and > 0 |

### Adjudication

- **RES-UFUZZ-004 (refreshBasket missing globalNonReentrant guard)** — Design weakness, not independently exploitable. Requires governance complicity. Defense-in-depth gap.
- **FORK-001** — Collateral plugins are not ERC1967 proxies. Delegatecall risk bounded.
- **FORK-002** — claimRewards delegatecall path live on mainnet, tradesOpen invariant holds.
- **All other candidates downgraded:** multi-proxy upgrade (self-only authorizeUpgrade), delegatecall claimRewards (static plugins), withdraw CEI (EVM atomicity).
- **Engine level: honest_zero**
- **`submit_ready` unchanged (0)**

### Remaining deferred vectors (lower probability)
- Oracle manipulation fork test for compromiseBasketsNeeded economics
- Cross-component state consistency: refreshBasket guard gap with rebalance race conditions

### Next: pivot to new target

Candidates: any fresh operator-selected Cantina/Immunefi slug.

## Completed arc: Metric OMM Sherlock Contest #1279 (closed honest-zero, v6.54)

**10 strategies, 29 test variants, 437 tests pass** across 3 crates. L-29 confirmed but withheld (prior audit ACK). `submit_ready` unchanged (0). **Do not reopen** without exact-audit-tree access.

## Completed arc: Euler v2 Cantina (closed scope-blocked, v6.53.1)

H4/PROP-EV2-004 FoT accounting desync confirmed technically (11 tests: 7 local + 4 fork) but **out of scope** per Cantina "weird tokens" + "EulerRouter misconfiguration" exclusions. **Do not reopen** without scope changes.

## Completed arc: LI.FI Diamond routing (closed scope-blocked, v6.51.23)

23/23 tests passing. EXECUTOR-ALLOWLIST-BYPASS confirmed but scope-blocked by Self-Crafted Calldata Risks. **Do not reopen** without bounty scope changes.

## Completed arc: Polymarket Cantina (closed honest-zero, v6.51.21)

51/51 tests passing, 14 hypotheses tested, all disproven or Low-Medium severity. Only finding: overflow DoS at `Trading.sol:654`. **Do not reopen** without new scope.

## Completed arc: Lombard cross-layer (closed acceptable-with-gaps, v6.51.19)

Substrate-confirmed honest-zeros (R1 rollback, R2 PDA collision, R3 Rust probes) + 1 round-level engineering_blocker. **Do not reopen** without new scope.

## Completed arc: Symbiotic Cantina (closed honest-zero, v6.51.22)

50+ contracts analyzed, 6 audits cross-checked, all fuzz harnesses pass. BurnerRouter no-access-control: confirmed but no net profit path. **Do not reopen** without new scope.
