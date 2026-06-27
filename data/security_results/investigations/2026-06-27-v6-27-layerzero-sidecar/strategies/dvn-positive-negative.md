# Strategy — DVN Positive / Negative Quorum Sequence (PROP-PKT-001, 002, 003, 005)

**Purpose:** exercise the send-side `_payDVNs` ↔ receive-side `_checkVerifiable` round-trip with a forged DVN signature set. Verify that (a) the encoded packet hash binds the receiver/receiver to its nonce; (b) the merged (default + custom) required DVN set cannot resolve to a 0-DVN config that auto-passes; (c) a quorum of optional DVNs alone cannot pass if `optionalDVNThreshold > requiredDVNCount` is violated; (d) a payload change invalidates the verification.

**Targets covered:** PROP-PKT-001 (packet-hash invariance), PROP-PKT-002 (DVN required-set resolution), PROP-PKT-003 (verify-quorum non-bypassability), PROP-PKT-005 (payload-hash binding).

**Symbolic model:**
- Sender OApp `oapp(sender)`, peer `peerOnChainB(receiver)` in OApp config.
- Send: `EndpointV2.send(params, refundAddr)` → `sendLib.send(packet, options, payInLzToken)` → `EndpointV2` collects fees, emits `PacketSent`.
- DVN quorum: `requiredDVNs[0..n+optionalDVNs[0..m)` with `optionalDVNThreshold ∈ (0, m]`.
- Verify: `ReceiveUln302.verify(packetHeader, payloadHash, confirmations)` per DVN → `commitVerification(packetHeader, payloadHash)` → `EndpointV2.verify(origin, receiver, payloadHash)`.

## Positive controls (must always succeed)

1. **Single DVN happy path**
   - Configure `requiredDVNs = [dvnA]`, `optionalDVNs = []`, `optionalDVNThreshold = 0`.
   - Sign packet header with dvnA (`confirmations = 1`).
   - Call `commitVerification`.
   - Expect: succeeds. `EndpointV2.lzReceive` succeeds. `inboundPayloadHash[receiver][srcEid][sender][nonce] == EMPTY_PAYLOAD_HASH` after clearing.
   - Capture: full forge trace, `IMPLEMENTATION_VERSION = "3.0.2"` confirmation, encoded packet shape.

2. **Quorum with optional DVNs**
   - Configure `requiredDVNs = [dvnA]`, `optionalDVNs = [dvnB, dvnC]`, `optionalDVNThreshold = 2`.
   - Sign with dvnA + dvnB + dvnC (`confirmations = 1`).
   - Expect: `commitVerification` succeeds.

## Negative controls (must always revert)

3. **Missing required DVN signature**
   - Configure `requiredDVNs = [dvnA, dvnB]`.
   - Sign with dvnA only.
   - Call `commitVerification`. Expect revert with `LZ_ULN_Verifying`.

4. **Optional DVN does not meet threshold**
   - Configure `optionalDVNThreshold = 2`, sign only dvnA + dvnB in optional pool (without required DVN(s) signing).
   - Expect revert `LZ_ULN_Verifying`.

5. **Wrong packet version byte / wrong dstEid**
   - Tamper packet header version byte to `0`. Expect `LZ_ULN_InvalidPacketVersion`.
   - Tamper dstEid to a non-default EID. Expect `LZ_ULN_InvalidEid`.

6. **Payload substitution (PROP-PKT-005)**
   - Run positive control 1.
   - Replace `_message` bytes after the hash was bound.
   - `commitVerification` reverts because `endpoint.verify` re-checks the stored hash via the `verifiable` view (the *stored* hash matches the presented one — but executor result is what changes).

## Adversarial (where we hunt)

7. **0-DVN configuration under edge merge**
   - Custom config: `requiredDVNCount = NIL_DVN_COUNT (0xff)`, `requiredDVNs = []`, `optionalDVNCount = NIL_DVN_COUNT`, `optionalDVNThreshold = 0`.
   - Default config: at least one required DVN.
   - Question: does `getUlnConfig` resolve to zero-DVN config?
   - Per source `messagelib/contracts/uln/UlnBase.sol:130`: NIL_DVN_COUNT clears the entire required/optional field. If default is then lifted, it must provide at least one DVN. `_assertAtLeastOneDVN` inside `getUlnConfig` is the catch — record its behavior.

8. **Reuse an existing hashLookup entry from a stale commit**
   - Sign-and-commit a packet. After `commitVerification`, `hashLookup` is *deleted* (per `_verifyAndReclaimStorage`). A subsequent DVN call to `verify(...)` with the *same* `(header, payloadHash)` creates a *new* entry. The next `commitVerification` then sees full quorum. Question: does this enable a stale acknowledgement loop? (Engine guard: each commitVerification finalizes the channel nonce; re-running commitVerification on the same nonce reverts with `_verifiable()` because `inboundPayloadHash != EMPTY_PAYLOAD_HASH`).

9. **Mutation of confirmations field by DVN**
   - First DVN call: `confirmations = 1`. Then second DVN call: `confirmations = type(uint64).max`.
   - Look at source: `_verified` requires `verification.confirmations >= _requiredConfirmation`. Higher set is the only check; **lower set is ignored if a later call lowers it**? Source `_verify` *overwrites*: `mapping(...)= Verification(true, _confirmations)`. Hence a malicious DVN could lower confirmations. **But**: the DVN does not gate; required-DVN-set determines *who* signs. A single DVN could be both required and optional, lowered after first sign → bypass possible only if optionalDVNThreshold > requiredDVNCount and DVN signs *both* required slot and optional slot. Engine-level hunt.

10. **PIO (Post-Initialization Override)**: `initializable()` permits `lazyInboundNonce == 0 || allowInitializePath`. Once a nonce path is initialized, can another caller initialize a new path with the same nonce from a *different* OApp? `_initializable` does not check sender-side cross OApp. Encode: oappA sends → oappB initializes same keypath (different `sender` field), expects no conflict because `lazyInboundNonce` is keyed by `[receiver][srcEid][sender]`.

## Engine harness plan

```python
# Pseudocode for the campaign. Concrete: foundry/test/LayerZeroDVNBypass.t.sol.
def round_trip(seed):
    fuzzer_seed = seed
    config = random_dvn_config(matrix_of_default_and_custom)
    # vector of intentional bad configs:
    bad_configs.append(("zero_requireddvns",   requiredDVNCount=NIL_DVN_COUNT,
                                                  optionalDVNCount=NIL_DVN_COUNT,
                                                  optionalDVNThreshold=0,
                                                  expect_zero_DVN_resolved=False))
    bad_configs.append(("missing_optional_threshold", optionalDVNThreshold=optionalDVNCount-1))
    bad_configs.append(("optional_only_no_required", requiredDVNs=[], optionalDVNThreshold=10))
    # expect _checkVerifiable to fail in each case
    run_forall(configs, 4 attempts per config)
```

The harness emits `IMPACT_USD:0` per attempt (no money moved) and a `PASS|DEAD_PASS|HARNESS_BUG` classification; honest-zero candidates place `FAIL_RATE: 0/N`. The Hamilton witness is documented in `evidence/dvn_positive_negative_<seed>.json` for each class.

## Modelled-negative outcomes

We model the assumption that the source-pinned `commitVerification` adds **two layered protections** (header format + quorum ≥ required-confirmations), so a single-vector bypass that breaks *both* at once looks unlikely. Even so, the per-`seed` replay attack class (strategy row 8) and the confirmations-overwrite malicious DVN (row 9) deserve explicit harnesses.
