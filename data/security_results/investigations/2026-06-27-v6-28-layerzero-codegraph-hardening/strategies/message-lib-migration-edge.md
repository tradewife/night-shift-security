# Strategy — Message-Library Migration Boundary

**Covers:** PROP-PKT-007, PROP-PKT-009

## Codegraph-hardening focus

- The manual structural map highlighted `EndpointV2.verify -> MessageLibManager.isValidReceiveLibrary` as the most central migration gate.
- Attack the exact grace-period boundary rather than only broad before/after behavior.

## Sequences

1. Default receive-library migration: old lib valid at `expiry - 1`, invalid at `expiry`, new lib valid at `expiry`.
2. Custom receive-library timeout: same exact boundary with OApp-specific override.
3. If either old lib verifies at equality, escalate as a plausible stale-lib delivery bug.

## Expected false positives

- Library registration / OApp authorization mistakes
- Test block-number setup mistakes around `vm.roll`
