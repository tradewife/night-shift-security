# Strategy — Executor Privilege / State Transition Boundary

**Covers:** PROP-PKT-004, PROP-PKT-005, PROP-PKT-006

## Codegraph-hardening focus

- Keep the packet-clear / replay surface in view while hardening the verification side.
- Reuse upstream `EndpointV2.t.sol` semantics for nilify, burn, skip, and exactly-once delivery when interpreting new results.

## Sequences

1. Reconfirm no replay after `_clearPayload`.
2. Reconfirm nilify preserves recommitability while burn / skip / executed slots do not.
3. Treat any divergence here as high-blast-radius because it couples verifier state to executor privilege.

## Expected false positives

- OApp mock behavior (`allowInitializePath`, receiver revert paths)
- Payload construction mismatch (`abi.encodePacked(guid, message)`)
