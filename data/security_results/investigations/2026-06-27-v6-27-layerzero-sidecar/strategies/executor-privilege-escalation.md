# Strategy — Executor Privilege Escalation & Replay Loop (PROP-PKT-004, 006)

**Purpose:** characterize and stress-test the `EndpointV2.lzReceive` entrypoint privilege boundary under:
1. Replay of a verified packet (intra-OApp, cross-chain, cross-executor).
2. Executor-side forced delivery of an unverified packet.
3. Phoney payInLzToken race conditions.
4. Cross-OApp nonce re-use in same receiver EID.

**Targets covered:** PROP-PKT-004 (executor privilege separation), PROP-PKT-006 (replay protection).

## What the source says

`EndpointV2.lzReceive` is `external payable` — *anyone* can call it. The protection is that `_clearPayload` reverts via `MessagingChannel._clearPayload` unless there is a stored hash in `inboundPayloadHash`. After deliver, the stored hash is **cleared** so a re-call on the same `(origin, receiver, nonce)` reverts.

`_verifiable` permits **re-verifying** if `inboundPayloadHash != EMPTY_PAYLOAD_HASH`, but lzReceive clears it. Therefore:

- Successful `lzReceive(receiver)` ⇒ payload consumed (cleared + receiver-side state).
- Replay attempt with same args reverts because `inboundPayloadHash == EMPTY_PAYLOAD_HASH`.

## Positive controls

1. **Honest executor flow**: DVN signs the proper `(header, payload)`, `commitVerification` succeeds, the executor then calls `lzReceive`. OApp receiver's `lzReceive` is called with proper `value > 0` for native tx.

2. **Honest pull-mode flow**: OApp caller (not executor) invokes `clear(oapp, origin, guid, message)` which is also gated on stored hash. Pull mode is documented in source.

## Negative / replay attacks

3. **Replay attempt**: after a successful `lzReceive`, call `lzReceive` again with the same args. Source `_clearPayload` reverts.

4. **Unverified packet attempt**: skip `commitVerification`, call `lzReceive` directly. `_clearPayload` reverts because stored hash is empty.

5. **Old nonce replay**: caller attempts `lzReceive` with non-verified origin with `nonce <= lazyInboundNonce`. `_verifiable` (and `_clearPayload`) revert because there is no stored hash for the nonce + payload pair.

6. **_additional_extension**: cross-executor. Two executor contracts both observing `PacketVerified` could race to call `lzReceive`. Whoever is included first wins; the second call reverts with `_clearPayload`. **Concern**: can the second one resubmit a *different* payload for the same nonce? `_clearPayload` keys by hash — see PROP-PKT-005.

## Adversarial — what we hunt

7. **PayInLzToken race**: per `EndpointV2._suppliedLzToken`, the protocol reads `IERC20(lzToken).balanceOf(address(this)) == supplied`. An attacker can fast-swap a major balance into the endpoint in the same block, so the `supplied != required` check on revert reverts with `LZ_ZeroLzTokenFee`. Better chance: cross-block front-run where the executor holds a previous balance; the contract should be invariant under token balance. **This is destructive**: any race condition lets the attacker pay zero fees on an inflated transaction and refund any overflow. Engine-level hunt.

8. **Bouncing native-fee refund**: `refundAddress` is set by sender. If OApp-controlled, attacker can claim as a fair game. The condition: `supplied > required` ⇒ refund excess to `refundAddress`. No exploit here, but misconfig (OApp-calls-quote with zero refundAddress == address(0) leads to loss of native). Documented for awareness; not a critical candidate.

9. **Composer-channel side-load**: `MessagingComposer` is a distinct layer between the endpoint and the OApp receiver. Sender-side `sendCompose` (offchain call) posts a `ComposeSent` event; receiver-side can call `lzCompose`. **Potential**: an off-chain Composer actor could enqueue impersonating anyone. Source study of `MessagingComposer.sol`: `oapporderedComposes[_from][_to][_composeFrom][_nonce]` mapping with no auth on the OApp-side except via `_assertAuthorized`. No obvious high-criticality bypass.

10. **Cross-OApp nonce re-use**: on the *receive-side*, `lazyInboundNonce[receiver][srcEid][sender]` increments per OApp `sender` field. Sender is bytes32 on EVM (the OApp address left-padded). So two OApps sending from `srcEidA` to the same `dstEidReceiver` will never collide. Good. Verify via forge: two distinct OApps → one receiver, same nonce, expect distinct sends stored under different keys (i.e. no collision).

11. **Endpoint lzToken recovery**: `recoverToken(...)` is owner-only. Owner takeover attack would be orthogonal but lower-impact. Documented.

## Engine harness plan

```solidity
contract LayerZeroExecutorReplayTest {
    function testLzReceiveUnverifiedReverts() public {
        bytes32 fakeHash = keccak256("nope");
        Origin memory origin = Origin(_eidA, sender, nonce=1);
        vm.expectRevert();
        endpoint.lzReceive(origin, receiver, guid, message, extraData);
    }

    function testLzReceiveReplayReverts() public {
        // round trip happy path
        // replay same args
        vm.expectRevert();
        endpoint.lzReceive(origin, receiver, guid, message, extraData);
    }

    function testLzCrossOAppNonceCollisionNeverCollides() public {
        // oappA and oappB send → expect independent lazyInboundNonce paths
    }
}
```

Emits `IMPACT_USD:0` and EXECUTOR_OK for honest-zero confirmation. Each test stamps `IMPACT_USD` to emphasize that **a Critical impact is measured in *delivered* state changes**, not in attempted calls.

## Boundary notes

`endpoint.lzReceive` itself is **not auth-gated**. The state-gating via `_clearPayload` is the actual auth. Engine guard: confirm `_clearPayload` reverts **before** invoking receiver-side logic. Source review of `MessagingChannel._clearPayload` will be cross-read at strategy-build time.
