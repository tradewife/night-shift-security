# Strategy — Message Library Migration Edge (PROP-PKT-007)

**Purpose:** characterize the attack surface when an OApp migrates its receive library *between* the source-side `PacketSent` and the destination-side `commitVerification`. Concretely: can a malicious owner of the receive library register a downgrade after a verified packet is in flight?

**Targets covered:** PROP-PKT-007 (message-lib migration safety).

## Architectural note

Each OApp's receive path is configured as:
- `defaultReceiveLibrary[eid]`: protocol-wide default.
- `receiveLibrary[oapp][eid]`: optional per-OApp override (set via `MessageLibManager.setReceiveLibrary(...)` invoked by OApp's delegate or admin).

`EndpointV2.isValidReceiveLibrary(receiver, srcEid, msg.sender)` returns true if:
- `msg.sender == receiveLibrary[receiver][srcEid]` && operator is valid, OR
- `msg.sender == defaultReceiveLibrary[srcEid]` && `isDefaultSendLibraryValid(...)`.

Once `endpoint.verify(...)` is called, the library *at the time of the call* enforces verification. Mid-flight library mutation could:
- Allow a lower-bar library to verify the same packet (a downgrade attack).
- Disallow a previously-valid library from verifying (DoS).

## Positive controls

1. **No-migration receive flow**: packet in flight + receiver library LibA → quorum verified → delivered.
2. **Migration post-delivery**: change receive library after `lzReceive`. New packet uses new library. Old delivery unaffected because the channel nonce is one-time.

## Adversarial — mid-flight migration

3. **Downgrade attack**: OApp owner sets LibB (weaker quorum) after packet sent. Receiver calls `commitVerification` on `ReceiveUln302` (same address — library address is *the same contract*, but its `setConfig` enforces config is acceptable).
   - Per source: `setReceiveLibrary` is gated on `MessageLibManager` producing a library that satisfies the OApp's path. The new lib needs to be registered *and* pass the migration delay (if any).
   - **Concern**: if the lib is mutated by re-pointing primitives to a library that *does* exist but has no quorum enforced at all, an attacker can register LibNull (an empty library) and bypass verification.

4. **Same-address mutation** — the malicious owner deploys a thin proxy that forwards `verify` to a different contract. `_assertSupportedEid` on receive side checks the registered library. **But** the `_checkVerifiable` inside `ReceiveUlnBase` keys off the *registered* ULN config — not the proxy's storage. This may be the actual edge.

5. **Pathological EIDs**: an OApp supports EIDs that have no default config. `setReceiveLibrary` for an unsupported EID should revert in `MessageLibManager.registerLibrary`. Verify via forge that any register path fails closed.

## Source-level predicates to be tested

From `protocol/contracts/MessageLibManager.sol`:

```
function registerLibrary(address _lib) external onlyEndpoint { ... emit LibraryRegistered(_lib); }
function setSendLibrary(address _oapp, uint32 _eid, address _lib) external isSendLib(_eid, _lib) { ... }
function setReceiveLibrary(address _oapp, uint32 _eid, address _lib) external isReceiveLib(_eid, _lib) { ... }
```

`isReceiveLib(_eid, _lib)` enforces that the lib is registered and supports the EID. Per the source-pinned `protocol/contracts/MessageLibManager.sol` at commit `0990059`, the gate is by `isSupportedEid(_eid, _lib)`. **Edge**: what if `MessageLibManager` accepts a registerLibrary but the lib does not actually return `true` for `isSupportedEid`? Read source: yes, `isSupportedEid` is from `IMessageLib` interface; it's a *contract call* into the lib. A lib's `isSupportedEid(eid)` is writable by its owner. Therefore the gate is **only as strong as** the lib's own implementation. A malicious lib could lie. **The core authoritative source of truth is the lib's owner not being able to lie through the endpoint**.

## Engine harness plan

```solidity
contract LayerZeroLibraryMigrationTest {
    function testMigrationDowngradeDoesNotBypassVerification() public {
        // happy path registered Lib, send packet
        // mutate receive library to a stub returning true for isSupportedEid but no quorum enforcement
        // commitVerification with the *new* lib (mock returns true trivially)
        // expect revert at endpoint.verify via _verifiable (no payload stored) OR
        // expect pass but with quorum frequency clearly *larger* than LibNull tolerated
    }
}
```

Emits `LIB_MIGRATION:OWNER_DRIVEN:pass-or-revert` per attempt.

## Stepped strategy

- **Step A**: confirm positive path. Done in `LayerZeroEndpointHarness.t.sol`.
- **Step B**: confirm set of receive libraries is OApp-controlled. Source review pass.
- **Step C**: confirm `setReceiveLibrary` is **owner-only** AND the new lib **must** satisfy `isSupportedEid`. Document a possible bypass if registering a malicious lib.
- **Step D**: combine with PROP-PKT-002 (DVN-set resolution) and PROP-PKT-003 (verify-quorum) to model a downgrade attack where the new lib registers a zero-DVN config.

## Engine verdict expectation

This is a *configuration-driven* attack vector. The endpoint's source review says the lib registration gate is robust IF the lib itself does not lie. **The hard-first principle says we should hunt the point where the lib CAN lie**, not the point where the endpoint misroutes. Considering the wide surface (a malicious OApp library deployed by anyone), **this is unlikely to yield Critical tier**. Engine-level honest-zero is the most likely result. Carry forward as a Phase 2A optional.
