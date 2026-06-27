# LayerZero V2 Endpoint + ULN302 Property Fan-In

**Investigation:** v6.27.0-layerzero-endpoint-uln302-sidecar-session30
**Target:** Immunefi LayerZero omnichain messaging bounty (max $15M critical, $2M V2 cap)
**Hard-first scope:** EndpointV2 `0x1a44076050125825900e736c501f859c50fe728c`, SendULN302 `0xbb2ea70c9e858123480642cf96acbcce1372dce1`, ReceiveULN302 `0xc02ab410f0734efa3f14628780e6e695156024c2`
**Pinned source commit:** `LayerZero-v2@0990059e3ee61ea95f45011cf7284243531fb4c3` (`audit` tag)
**Hard first principle:** the *messy intersection* where DVNs, executor, message lib, and OApp peer trust boundaries intersect. Single-contract nits deprioritized.

## Trust model smashed against the source

LayerZero V2 separates four orthogonal privileges that all have to line up to deliver a cross-chain packet:

| # | Privilege | Surfacing contract(s) | Source reference |
|---|-----------|------------------------|-------------------|
| 1 | OApp configured peer / nonce / lazyInboundNonce | EndpointV2 → `MessagingChannel` | `protocol/contracts/EndpointV2.sol:200-260`, `protocol/contracts/MessagingChannel.sol` |
| 2 | Send library routing + nonce bump + DVN job assignment | EndpointV2 → `MessageLibManager` + `SendUln302` | `protocol/contracts/MessageLibManager.sol`, `messagelib/contracts/uln/uln302/SendUln302.sol:48-78` |
| 3 | DVN set + confirmation threshold per (oapp, dstEid) | `UlnBase._setConfig` + `getUlnConfig` | `messagelib/contracts/uln/UlnBase.sol:178-216` |
| 4 | Receive-side verification (all required + `optionalDVNThreshold` optional) | `ReceiveUln302.commitVerification` + `ReceiveUlnBase._checkVerifiable` | `messagelib/contracts/uln/uln302/ReceiveUln302.sol:38-65`, `messagelib/contracts/uln/ReceiveUlnBase.sol:97-114` |

A bypass in any one of these gives the OApp receiver the ability to act on a packet the protocol should have rejected.

## Pipeline packets (encoded packet flow)

```
EndpointV2.send
  → ISendLib(SendUln302).send
    → SendUlnBase._payDVNs (assigns to requiredDVNs[0..n)+optionalDVNs[0..m), pays native)
  → EndpointV2 stores nothing in caller-visible state
  → emits PacketSent(encodedPacket, options, sendLibrary)

DVN[].verify(packetHeader, payloadHash, confirmations)
  → ReceiveUln302.verify → ReceiveUlnBase._verify
  → hashLookup[keccak256(header)][payloadHash][dvn] = (true, confirmations)

ReceiveUln302.commitVerification(packetHeader, payloadHash)
  → assert header correctness (length=81, version, dstEid)
  → _verifyAndReclaimStorage → checks quorum, then deletes per-dvn storage
  → EndpointV2.verify(origin, receiver, payloadHash)
    → assert messageLib permission + initializable + verifiable
    → inserts payloadHash into channel

Executor OR OApp (pull)
  → EndpointV2.lzReceive(origin, receiver, guid, message, extraData)
    → _clearPayload (clears the stored hash to defeat reentrancy)
    → ILayerZeroReceiver(receiver).lzReceive{value: msg.value}(...)
```

## Canonical property table

| property_id | surface | invariant | bug class | kill criteria | evidence required |
|-------------|---------|-----------|-----------|---------------|-------------------|
| **PROP-PKT-001** — packet-hash invariance | `EndpointV2._send` → `Packet.guid = GUID.generate(nonce, eid, sender, dstEid, receiver)` | The 22-byte GUID is fully determined by `(nonce, srcEid, sender, dstEid, receiver)`. Adding/removing `message` bytes does not change the GUID. The hash of the encoded packet header (`PacketV1Codec`) is also fully determined by these six fields. | hash collision, GUID forgery | Any two distinct `(nonce, sender, ..., dstEid, receiver)` tuples producing equal GUID is a benign collision; a single tuple producing two distinct GUIDs is a fatal invariant break. | forge-level: two `_send` calls with mutated payloads collide on GUID; assertion `assertEq(packet1.guid, packet2.guid)` for fixed tuple. |
| **PROP-PKT-002** — DVN required set non-decreasing | `_setDefaultUlnConfigs` + `getUlnConfig` merge logic in `UlnBase` | Resolved ULN config for any (oapp, eid) has `requiredDVNCount + (optionalDVNThreshold > 0)` strictly greater than the same for the default config alone (modulo `NIL_DVN_COUNT = 0xff` override operator). Default must have at least one DVN. | config regression, optional-only quorum bypass | A config that resolves to `requiredDVNCount == 0 && optionalDVNThreshold == 0` (after merging oapp+NIL+default). Today `_assertAtLeastOneDVN` reverts this in `getUlnConfig` — visual fuzz should confirm. | Python resolver: enumerate `(default, custom)` matrix incl. `NIL_DVN_COUNT` and `DEFAULT=0` overrides; observe no collapse to zero-DVN config. |
| **PROP-PKT-003** — verify-quorum non-bypassability | `ReceiveUln302.commitVerification` → `ReceiveUlnBase._checkVerifiable` | A `commitVerification` call must not insert into the endpoint channel unless at least one of the required DVNs (or `optionalDVNThreshold` of optional) has signed with `confirmations >= config.confirmations`. Calling `commitVerification` without the required quorum must revert with `LZ_ULN_Verifying` or `_verifiable()` check failure. | quorum bypass, hash-rebound against unset storage | A round-trip where `commitVerification` succeeds but `_checkVerifiable` would have returned false. | forge fork harness: malicious DVN fork where optionalDVN signs alone, requiredDVN silent. Expect `lzReceive` revert. |
| **PROP-PKT-004** — executor privilege separation | `EndpointV2.lzReceive` (any caller) | Anyone can call `lzReceive`, but `_clearPayload` removes the stored hash first; receptor's `lzReceive` is the one that finally mutates receiver state. Executor cannot replay verified packets; non-executor cannot deliver unverified packets because `_clearPayload` reverts in `endpoint.verify` if not yet present. | privilege escalation, replay | A second `lzReceive` for the same `(origin, receiver, nonce)` succeeds (replay). An `lzReceive` succeeds when `endpoint.verify` was never called. | forge: dup `lzReceive` + verify never called. |
| **PROP-PKT-005** — payload-hash binding | `_inbound` stores `keccak256(payload)` keyed by `(receiver, srcEid, sender, nonce)` | `endpoint.verify` requires the executor to present a payload whose hash matches the stored value. Switching payload bytes fails because `O(n) bytes -> hash` is collision-free. | downstream state driven by unverified payload | Two distinct payloads submitted as same `(origin, receiver, nonce)` get to choose which one is *executed*. | pure python: collision-finding attempt is expected to fail to find any; document minimal entropy. |
| **PROP-PKT-006** — replay protection | `inboundPayloadHash` + `_clearPayload` + `_verifiable`'s `nonce > lazyInboundNonce` | The same `(srcEid, sender, nonce)` cannot be re-delivered after it has cleared. The nonce is monotonically increased per (sender, srcEid, receiver, dstEid) via `outboundNonce[...]++`. | nonce poisoning, replay across OApp paths | A caller in a *different* OApp path (different receiver) gets the same nonce to be accepted on the same src EID. | forge: simulate two OApps send → receive with colliding nonce; expected revert. |
| **PROP-PKT-007** — message-lib migration safety | `MessageLibManager.registerLibrary` (`setDefaultSendLibrary`/`setDefaultReceiveLibrary` override per OApp) | If an OApp migrates from messagelib A to messagelib B after a packet is in-flight, B cannot downgrade or skip verification. The receive-side lib registered *at verify time* must produce the quorum check. | downgrade attack, lib migration race | An owner migrates the receive lib mid-flight, and the new lib signs an unverified packet. | forge: `setReceiveLibrary` between `PacketSent` and `commitVerification`; verify new lib must still enforce quorum. |

### Property table provenance

Each row references the **head commit** of the cloned source so all hand-rolled assertion checks map directly to a hash-pinned file:

| row | source path (commit `0990059e3ee61ea95f45011cf7284243531fb4c3`) |
|-----|------------------------------------------------------------------|
| 001 | `protocol/contracts/EndpointV2.sol`, `protocol/contracts/libs/GUID.sol`; `protocol/contracts/messagelib/libs/PacketV1Codec.sol` |
| 002 | `messagelib/contracts/uln/UlnBase.sol` (lines 178-216 + `_assertAtLeastOneDVN`) |
| 003 | `messagelib/contracts/uln/uln302/ReceiveUln302.sol` lines 38-65; `messagelib/contracts/uln/ReceiveUlnBase.sol` `_checkVerifiable` |
| 004 | `protocol/contracts/EndpointV2.sol` `lzReceive` lines 116-124 + `_clearPayload` (`MessagingChannel`) |
| 005 | `protocol/contracts/EndpointV2.sol` `_verifiable()` lines 254-262 + `MessagingChannel.inboundPayloadHash` |
| 006 | `protocol/contracts/MessagingChannel.sol` (`outboundNonce`, `lazyInboundNonce`) + `EndpointV2.lzReceive` |
| 007 | `protocol/contracts/MessageLibManager.sol` (send/receive library registration + isValid*Library check) |

## Out-of-scope properties (still named so future sessions don't drift)

- **OApp-level misconfiguration**: explicitly out per Immunefi bounty rules.
- **Off-chain DVN failures**: out of scope; only collateral damage via configuration mutation is testable.
- **Worker admin/governance failures in DVN/MultiSig**: DVN's `setSigner`, `setQuorum`, `grantRole` flow is locked off `MESSAGE_LIB_ROLE` to the DVN itself; the `onlySelf` modifier requires `address(this)`. Multi-sig quorum is the *bigger* trust assumption than the message-lib code.
- **DVN fee edge cases**: irrelevant to in-scope critical impact unless combined with quorum issues.
- **OFT/ONFT impact**: per scope, Low severity. Phase 2A contingent only.

## Empirical-FNR framing (per SPEC.md §3.2 + lab notebook calibration)

This target is, as of 2026-06-27, the 3rd empirical-FNR datum candidate after Ethena + Marginfi. **An honest-zero outcome is the most likely result.** We honor the Mandatory Falsification Protocol:

1. Falsifier pass: simulate an OApp using a zero-DVN resolved config + a replay scenario before claiming honest-zero.
2. Engine-level honest-zero is *only* claimable after (a) `forge test` runs without invariant failures, and (b) the source-only review surfaces no obvious bypass path that the harness doesn't reach.
3. Saturation is bounded, not asserted. Audit-saturation framing per SPEC §3.2: hard-first over OFT/V1/Aptos is a *priority choice*, not a *known saturation claim*.
