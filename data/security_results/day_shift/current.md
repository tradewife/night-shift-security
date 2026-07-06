# Session plan — current

**Status: in-progress (2026-07-06). Euler v2 v6.53 session 2 — corpus-correlated hard-first looping campaign completed. FoT PoC confirmed.**

## Active arc: Euler v2 EVC cross-vault contagion (v6.53 corpus-correlated loop)

**Bounty:** https://cantina.xyz/bounties/4d285eee-602e-440a-845e-25e155cec26a
**Workspace (kept-local):** `data/security_results/investigations/2026-07-06-euler-v2-evc-cross-vault/`

### Session-2 results

- **Corpus correlation**: Synced AuditVault (2383 findings) + Solodit (159 patterns); 10+ queries → 9 classified findings in `corpus_correlation_session2.md`. Dispositions: 3 already-fixed (stales/MEV/min-liquidation), 1 analogous-but-guarded (ERC4626 donation), 1 unguarded-and-reachable promoted to PROP (ERC4626 vault fees as oracle).
- **Property promotion**: PROP-EV2-008 (ERC4626 vault with fees as oracle input) added to `property_candidates.md`. INV-EV2-010 (resolveOracle ERC4626 convertToAssets ignores vault fees) appended to `invariants.md`.
- **EPO bootstrap**: 9/9 submodules cloned. `remappings.txt` created. Source analysis confirmed all 3 oracle adapters have explicit `maxStaleness` validation. Foundry profile updated with EPO remappings.
- **FoT PoC (H4/PROP-EV2-004)**: Fork-free harness deploying full EVK stack + Permit2 bypass. 6 tests PASS confirming:
  - `totalAssets()` = 100k but `balanceOf(vault)` = 99k (100 bps divergence)
  - Share price = 1.0 but actual backing = 0.99 (masks deficit)
  - Cross-vault collateral overvalued by ~101 bps
  - Virtual offset (1e6) exhausted by realistic deposit volume
- **`submit_ready` unchanged** (0). Verdict: actionable property confirmed; fork-verified cross-vault liquidation PoC needed before submission decision.

### Session-3 blocking items

- EPO forge build (pendle relative-import symlink issues)
- Slither run on EPO
- PROP-EV2-008 fork test (fee-charging ERC4626 vault + mainnet EulerRouter)
- Full EVC batch fork harness for H1/H3/H5 with live `verifiedArray()` vault addresses
- Pull live perspective vault addresses (requires Cantina docs or on-chain resolution)

### Closeout framing

v6.52/v6.53 closes when 1 fork-verified HIGH+ candidate OR diminishing returns on Primary Target Subsystem.

## Completed arc: LI.FI Diamond routing (Cantina $1M bounty)
[scope-blocked pivot per v6.51.23]

## Completed arc: Polymarket Cantina (closed honest-zero)
[preserved]

## Concurrent arc: Makina Contracts (closing)
[preserved]
