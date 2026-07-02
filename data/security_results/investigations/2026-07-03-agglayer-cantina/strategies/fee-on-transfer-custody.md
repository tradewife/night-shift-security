# Strategy: Fee-on-transfer custody (H-FEE-001)

## Properties

- `PROP-AGG-007`

## Surface

- `AgglayerBridge.bridgeAsset` leaf amount vs actual custody (`contracts/mocks/FeeOnTransferERC20.sol` available in clone)
- Rust `NetworkState` balance uses declared exit amounts, not post-fee received

## Plan

1. Hardhat: extend BridgeV2 patterns with `FeeOnTransferERC20` deposit; compare `BridgeEvent` amount vs `balanceOf(bridge)`.
2. Cross-check pessimistic proof: outgoing exit amount > local balance must revert (`e2e_local_pp_overflow_attempt` in `pessimistic-proof-test-suite`).
3. Promotion requires custody deficit enabling over-claim on destination network.

## Status

- Mock token present; dedicated NSS/clone executable not yet run this campaign.
