# STRAT-S12 — BR-CL-001 CLAdapter initateDeposit cache redirect (v6.51.L amplification)

## Round metadata

| Field | Value |
|------|-------|
| Round | v6.51.L |
| Lead | `BR-CL-001`, `EVM-CL-REDIRECT`, secondary `EVM-011-AMOUNT` |
| Skill chain | `operator-recon` → `codegraph-x-ray` → `agentic-strategy-generation` → `fuzz-scaffolder` → `ultrafuzz-discovery` |
| Evidence | `evidence/evm-cladapter-redirect-clean.log`, `evidence/evm-cladapter-bridge-fullset.log`, `evidence/evm-prop-xr-final.log`, `evidence/consortium-parser-regression.log` |

## Goal

Continue the hard-first loop after the v6.51.12 closure of
`SIG-XR-001-ROLLBACK`. The user explicitly forbade checkpointing out of the
gate; the orchestrator had to keep generating leads, dropping benign
ones and attacking any plausible bridge cross-layer divergence until either
a fund-loss-looking chain shows up or the budgeted EVM substrate is exhausted.

This round prioritises the EVM `LombardTokenPoolV2` amount-binding angle and
the legacy Chainlink `CLAdapter` cached-payload decoupling. The latter was
the only lead that survived validator semantics on the legacy Bridge substrate.

## Top leads revisited

| Lead | Primary file | Outcome |
|------|--------------|---------|
| `BR-CL-001` CLAdapter cache redirect (`initiateDeposit`) | `contracts/bridge/adapters/CLAdapter.sol` | **Reproduced** — see below |
| `EVM-CL-AMOUNT` `LombardTokenPoolV2.releaseOrMint` amount binding | `contracts/bridge/LombardTokenPoolV2.sol` | Demonstrates EVM-011 fixture is active, but is currently mid-construction (no full Vault ↔ Bridge deltas) |
| `BR-MBOX-001` Solana mailbox handshake replay | `programs/mailbox/src/lib.rs` | Deferred (validator unreachable in this session) |
| `SIG-CR-001-OOB` consortium parser differential | `programs/consortium/src/utils/session_payloads.rs` | **Killed** by Rust regression test |

## Reproduction 1 — CLAdapter cache redirect (the submission candidate)

The legacy Chainlink adapter stores the immediately-preceding
`Bridge.deposit` payload and burned amount in `_lastPayload` / `_lastBurnedAmount`.
A subsequent legitimate `LombardTokenPool.lockOrBurn` from a CCIP `onRamp`
caches the new payload but is redirected to the previous (attacker-controlled)
payload via the Branch:

```solidity
if (_lastPayload.length > 0) {
    lastBurnedAmount = _lastBurnedAmount;
    lastPayload = _lastPayload;
    _lastPayload = new bytes(0);
    _lastBurnedAmount = 0;
} else {
    // first-time path
}
```

In source semantics, the onRamp CCIP message ends up:

- emitting `LockedOrBurned(amount = _lastBurnedAmount = seededNetAmount)` instead of `amount = ccipAmount`;
- returning `destPoolData = abi.encode(sha256(_lastPayload)) = abi.encode(sha256(attacker.payload))`;
- **draining** `ccipAmount - seededNetAmount` of `lbtc` from the pool into the source `aCLAdapter` (stuck);
- the destination `releaseOrMint` then mints `seededNetAmount` (45_000_000) on chain B to the **attacker receiver** — not the CCIP victim's `victimReceiver`.

The fixture proves:

```ts
✔ NSS: CLAdapter cached payload redirects a later CCIP lock to an attacker payload (82ms)
```

And the cross-layer + Bridge full set remains green:

```
21 passing (2s)
```

with all bridge invariants preserved. The new test sits in
`tests/Bridge.ts` next to the legacy "With Chainlink Adapter" describe and
adds no coupling outside the existing `MockCCIPRouter` / `CCIPRMNMock`
substrate.

### Why it is real impact

1. **CCIP victim loses funds.** The legitimate sender pays `ccipAmount` and
   ends up with `victimReceiver = 0` on the destination bridge, while the
   attacker — who never paid anything to the source side — gets
   `seededNetAmount = seededAmount - 10% commission`.
2. **Adapter holds stuck funds.** `aCLAdapter` retains `ccipAmount - seededNetAmount`
   on the source chain but is not authorised to unwind it back to the pool.
3. **The redirect compounds as the only CLI path.** Both legs of the bug
   exist only because `_lastPayload` is not invalidated on
   `initiateDeposit` flow, which is the documented behaviour of the legacy
   adapter.

## Reproduction 2 — LombardTokenPoolV2 amount binding (EVM-011 strengthener)

The `LombardTokenPoolV2.releaseOrMint` permits the destination `BridgeV2._withdraw`
to mint an arbitrarily different amount `B` while still returning
`destinationAmount = sourceDenominatedAmount = claimedCcipAmount` to CCIP.

Test:

```ts
✔ permits bridge mint amount B while returning CCIP destinationAmount A
```

This is meaningful only if a non-compromised source pool produces a
mismatched `sourcePoolData` or the destination `BridgeV2` is somehow
attacker-controlled. Operator-triage currently bounds this as helpful
context for the chain-of-trust analysis but **not as a submission-ready
finding** because the bug requires a separate source compromise vector.

## Killed leads this round

### SIG-CR-001-OOB / consortium parser differential

A 1060-byte crafted `UpdateValSetPayload` was constructed in Node.js with
overlapping offset windows so that `ethers.concat(decode()` returned
benign-looking validators while the on-chain linear parser would have slid
to read a malicious validators slice.

Negative regression test:

```rust
#[test]
fn test_nss_noncanonical_offsets_rejected_as_leftover_data() { ... }
```

Output:

```
test utils::session_payloads::tests::test_nss_noncanonical_offsets_rejected_as_leftover_data ... ok
```

The Solana linear parser correctly raises
`ConsortiumError::LeftoverData` and refuses the buffer. The class of bug is
genuinely benign. **Closed as honest-zero.**

### Heuristic checks already attempted (and killed) previously

- `BR-MBOX-001` Landau-byte exhaustion → already closed in v6.51.11.
- Solana Bascule vs GMP domain separation → no live validator reachable.

## Carry-forward

1. Promote `BR-CL-001` to human-only review queue. The current proof lives in
   the legacy Chainlink adapter (Bridge.ts), so it is not a cross-source
   deployment risk. The Foundry + Lombard audit teams should still see it.
2. Continue iterating the LombardTokenPoolV2 amount-binding path with a
   stronger fixture that proves the B > A side picks up an attractive
   source-compromise vector (e.g. inter-chain replay of Bridge deliverables).
3. Continue the Rust-side Crucible state expansion on `lombard_token_pool`
   for validator-reachable flows; the rust regression
   `consortium-parser-regression.log` shows the parse path is fully tested.
4. Maintain the cross-layer ledger mock-pool substrate in
   `programs/lombard_token_pool/idls/` so the next iteration can drop a
   Crucible scenario without re-bootstrapping.

## Status

- `SIG-XR-001-ROLLBACK`: closed (v6.51.12)
- `SIG-CR-001-OOB-DOS`: closed (this round, Rust regression)
- `PROP-XR-EVM-006/-007/-010`: green (this round)
- `PROP-XR-EVM-011` amount binding: green, kept as enhancemenet vector
- `BR-CL-001` cache redirect: **green validator-fidelity proof**
