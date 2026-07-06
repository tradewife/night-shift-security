# Session plan — current

**Status: in-progress (2026-07-07). Euler v2 v6.53 session 2 FoT PoC completed — scope-blocked, pivot needed.**

## Active arc: Euler v2 EVC cross-vault contagion (v6.53 corpus-correlated loop)

**Bounty:** https://cantina.xyz/bounties/4d285eee-602e-440a-845e-25e155cec26a
**Workspace (kept-local):** `data/security_results/investigations/2026-07-06-euler-v2-evc-cross-vault/`

### Session-2 results — H4/PROP-EV2-004 (FoT accounting desync)

**SCOPE VERDICT: OUT OF SCOPE** per Cantina rules — "Issues related to non-standard tokens and their behaviors (i.e. weird-tokens)" applies to fee-on-transfer tokens. Cross-vault exploit path also OOS per "Issues related to misconfiguration in EulerRouter... resolving ERC4626 vaults with insecure convertToAssets method." No known production vault uses an FoT underlying.

- **11 tests total**: 7 local (full EVK stack, Permit2 bypass, cross-vault borrow exploit) + 4 fork (mainnet EVC + EulerRouter). All PASS.
- **Fork-verified inflation propagation**: Real EulerRouter on mainnet fork correctly calls fotVault.convertToAssets() which reads the inflated totalAssets(). Oracle pipeline never checks actual balanceOf(vault).
- **Bad debt demonstrated**: 100 bps divergence per deposit cycle. Compounds with each deposit. On liquidation, protocol recovers only 99% of stated collateral.
- **Cross-vault borrow exploit**: Alice borrows 250 more per 100k deposit than actual backing by using inflated fotVault shares as EVC collateral.
- **Corpus correlation**: 9 findings classified across AuditVault + Solodit. EPO oracle staleness confirmed fixed.
- **Key test files**: `EulerV2Harness.t.sol` (7 local tests), `EulerV2ForkVerify.t.sol` (4 fork tests)
- **`submit_ready` unchanged** (0). Finding is technically valid (EVK pullAssets bug) but OOS for bounty.

### Next: pivot to new target

- PROP-EV2-008 (ERC4626 fee vault as oracle) — also OOS per "Issues related to misconfiguration in EulerRouter"
- EPO slither — low priority, all oracle staleness confirmed fixed at source
- Full EVC batch fork harness for H1/H3/H5 — lower signal given scope constraints

## Completed arc: LI.FI Diamond routing (Cantina $1M bounty)
[scope-blocked pivot per v6.51.23]

## Completed arc: Polymarket Cantina (closed honest-zero)
[preserved]

## Concurrent arc: Makina Contracts (closing)
[preserved]
