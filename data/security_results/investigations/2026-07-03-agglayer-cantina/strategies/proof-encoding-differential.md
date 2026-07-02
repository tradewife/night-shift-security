# Strategy: Proof Encoding Differential

## Properties Covered

- `PROP-AGG-001`
- `PROP-AGG-008`
- `PROP-AGG-009`

## Hypothesis

The most valuable mismatch would be a proof that is valid for one set of Rust public values but accepted by Solidity as if it proved another set of roots, network IDs, route selectors, or aggchain hash.

## Plan

1. Generate deterministic PP vectors with `pessimistic-proof-test-suite`.
2. Decode `PessimisticProofOutput::bincode_codec()` fields.
3. Reconstruct Solidity `_getInputPessimisticBytes` for both pure `VerifierType.Pessimistic` and `VerifierType.ALGateway`.
4. Mutate one field at a time: previous PP root, origin network, L1 info root, empty LER zero mapping, aggchain hash, route selector.
5. Require all mismatches to fail before root consolidation.

## Expected False Positives

- Harness encoding of Rust bincode differs from the on-chain SP1 public value wrapper.
- ALGateway route mocks over-approximate real gateway checks.
- Test vector uses stale source revision relative to deployed contracts.

## Promotion Evidence

- Minimal vector and Solidity test showing accepted mismatched public values.
- State diff showing `lastLocalExitRoot`, `lastPessimisticRoot`, or GER changed under a mismatched proof.
