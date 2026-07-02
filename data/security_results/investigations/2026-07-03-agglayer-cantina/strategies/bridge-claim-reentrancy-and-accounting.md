# Strategy: Bridge Claim Reentrancy and Accounting

## Properties Covered

- `PROP-AGG-006`
- `PROP-AGG-007`
- `PROP-AGG-002`
- `PROP-AGG-003`

## Hypothesis

`claimMessage` intentionally omits `nonReentrant` to support composability. The nullifier should already be set, but composability plus fee-on-transfer/remapped wrapped tokens can still expose accounting mismatches between leaf amount, bridge custody, wrapped supply, and callback behavior.

## Plan

1. Build malicious `IBridgeMessageReceiver` that reenters:
   - same `claimMessage`,
   - paired `claimAsset`,
   - fresh `bridgeAsset`,
   - `bridgeMessageWETH` if WETH mode is enabled.
2. Add adversarial tokens:
   - fee-on-transfer ERC20,
   - token returning unusual metadata,
   - wrapped token with overridden burn/mint semantics where reachable through sovereign bridge variants.
3. For each run, assert:
   - same leaf cannot be claimed twice,
   - BridgeEvent amount equals actual custody/burn delta,
   - wrapped supply plus bridge custody equals settled claims.

## Expected False Positives

- Mock proofs bypass real SMT inclusion constraints.
- Non-standard token is out of scope if it requires malicious token deployment by the victim.
- Sovereign bridge remapping may not be in the Cantina primary scope.

## Promotion Evidence

- Reentrant trace or accounting state diff that drains or mints beyond settled leaf amounts on production-equivalent contracts.
