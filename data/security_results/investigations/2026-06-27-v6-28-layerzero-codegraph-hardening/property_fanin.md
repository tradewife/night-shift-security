# LayerZero V2 Endpoint + ULN302 Property Fan-In

**Investigation:** v6.28.0-layerzero-endpoint-uln302-codegraph-hardening-session31  
**Target:** EndpointV2 + SendUln302 + ReceiveUln302 packet lifecycle  
**Pinned source commit:** `LayerZero-v2@0990059e3ee61ea95f45011cf7284243531fb4c3`

## Codegraph-first note

- `codegraph init` completed successfully against `sources/layerzero/repo`.
- Current `codegraph` build indexed only 5 non-Solidity files in this workspace, so the mandatory first-pass structural step surfaced a tooling blind spot rather than a usable Solidity call graph.
- Resulting hardening path: treat the codegraph miss itself as a negative-signal artifact, then derive the structural map manually from the pinned Solidity sources plus upstream `protocol/test` and `messagelib/test` fixtures.

## Central lifecycle clusters after the codegraph pass

1. `EndpointV2.verify` ↔ `MessageLibManager.isValidReceiveLibrary` ↔ timeout/grace-period edges
2. `ReceiveUln302.commitVerification` ↔ `ReceiveUlnBase._verifyAndReclaimStorage` ↔ `EndpointV2.verify`
3. `MessagingChannel._clearPayload` ↔ nilify / burn / skip / re-verify state transitions
4. `UlnBase.getUlnConfig` ↔ default/custom/NIL merge semantics used by both send and receive legs

## Canonical property table

| property_id | surface | invariant | bug class | kill criteria | evidence required |
|-------------|---------|-----------|-----------|---------------|-------------------|
| PROP-PKT-001 | PacketV1 header + GUID binding | Header hash and GUID stay deterministic for a fixed `(nonce, srcEid, sender, dstEid, receiver)` tuple. | packet forgery | same tuple yields multiple hashes or GUIDs | codec tests, selector parity |
| PROP-PKT-002 | `UlnBase.getUlnConfig` | Resolved ULN config cannot collapse to zero effective DVNs. | config collapse | resolved config has `requiredDVNCount == 0 && optionalDVNThreshold == 0` | resolver matrix |
| PROP-PKT-003 | `ReceiveUln302.commitVerification` | No commit without required quorum. | quorum bypass | commit succeeds while `_checkVerifiable` is false | Foundry sequence |
| PROP-PKT-004 | `EndpointV2.lzReceive` | Verified packets are exactly-once deliverable. | replay / privilege | second delivery succeeds or unverified delivery succeeds | Foundry sequence |
| PROP-PKT-005 | `EndpointV2.verify` / payload hash | Stored payload hash must bind executor payload bytes. | payload substitution | two payloads can execute for one stored slot | payload hash check |
| PROP-PKT-006 | `MessagingChannel` nonce state | Nonce progression is path-scoped and ordered. | replay / bucket collision | different paths share a valid replay bucket | nonce-state tests |
| PROP-PKT-007 | receive-lib migration | Library migration cannot silently skip verification requirements. | downgrade / migration race | old or new lib bypasses expected verification rules | timeout / migration tests |
| PROP-PKT-008 | `ReceiveUlnBase._verifyAndReclaimStorage` | Successful commit must delete DVN attestations for that `(headerHash, payloadHash)` tuple, forcing fresh signatures before any recommit. | ghost quorum reuse | second commit succeeds without fresh DVN verify | storage-reclaim test |
| PROP-PKT-009 | `MessageLibManager.isValidReceiveLibrary` | Old receive library remains valid only while `timeout.expiry > block.number`, not at equality. | one-block-over-grace stale verification | old lib still verifies at `block.number == expiry` | boundary verify tests |
| PROP-PKT-010 | `hashLookup[headerHash][payloadHash][dvn]` | Quorum is header-scoped as well as payload-scoped; attestation on header A cannot commit header B. | cross-header quorum reuse | commit on header B succeeds using header A signatures | cross-header commit test |

## New micro-hypotheses

1. **H4 stale-lib boundary leak**  
   If default/custom receive-library timeout uses `>=` semantics in practice rather than the source-level `>`, an old library may retain one extra verification block during migration.

2. **H5 ghost-quorum reclamation miss**  
   If `commitVerification` leaves DVN attestations behind for a committed tuple, an attacker could re-commit without fresh DVN work after nilify or path churn.

3. **H6 header-scope bleed**  
   If quorum storage is keyed too coarsely, a valid attestation on one packet header might be replayable onto another header with the same payload hash.
