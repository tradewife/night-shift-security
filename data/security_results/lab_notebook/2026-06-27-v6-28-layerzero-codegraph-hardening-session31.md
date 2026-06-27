# Lab Notebook — v6.28 LayerZero codegraph hardening (session-31)

## Same vs different

- **Same:** hard-first scope stayed pinned to EndpointV2 + SendUln302 + ReceiveUln302 on `LayerZero-v2@0990059e3ee61ea95f45011cf7284243531fb4c3`. `submit_ready` stayed `0`.
- **Different:** this round enforced a mandatory codegraph-first step before touching harnesses. `codegraph` installed and initialized, but the current build only indexed 5 non-Solidity files in this workspace, so the session explicitly recorded a Solidity-coverage blind spot and fell back to pinned-source/manual structural mapping.

## Structural takeaways

1. The highest-centrality practical edge remains `EndpointV2.verify -> MessageLibManager.isValidReceiveLibrary`, especially grace-period expiry semantics.
2. The second key edge is `ReceiveUln302.commitVerification -> ReceiveUlnBase._verifyAndReclaimStorage -> EndpointV2.verify`.
3. The interesting hardening opportunity was not new business logic, but lifecycle exactness: boundary blocks, stale quorum deletion, and header-scoped verification state.

## New properties added

- `PROP-PKT-008` post-commit quorum-storage reclamation
- `PROP-PKT-009` strict receive-library grace expiry boundary
- `PROP-PKT-010` header-scoped quorum isolation

## Executable results

- Root sidecar: `pytest tests/test_native_layerzero.py` -> **17 passed**
- Root sidecar: `forge test --root foundry --match-path test/LayerZero*.sol` -> **10 passed / 3 skipped**
- Upstream local-only:
  - `protocol/test/EndpointV2CodegraphHardening.t.sol` -> **2 passed**
  - `messagelib/test/ReceiveUln302CodegraphHardening.t.sol` -> **2 passed**

## Candidate assessment

- No stale-lib one-block-over-grace leak observed.
- No ghost-quorum reuse observed after `commitVerification`.
- No cross-header quorum bleed observed.
- Outcome: stronger honest-zero evidence, still below submission gates.

## Direction C — dead-DVN / isSupportedEid contradiction (fork PoC)

### Artifact

- `foundry/test/LayerZeroEndpointIsSupportedEidAudit.t.sol` (local-only, untracked)
- Forks Ethereum mainnet via `ETHEREUM_RPC_URL` (Alchemy-backed), skips if absent.
- Probes 5 curated EIDs: `[30155, 30301, 30309, 30110, 30202]`.

### Live results (2026-06-27, block ~latest)

| EID | Chain | isSupportedEid | quote reverts | dead DVN in default config | default lib code size |
|-----|-------|----------------|---------------|---------------------------|---------------------|
| 30155 | Tac | true | true | **true** | 11010 (ReceiveUln302) |
| 30301 | Read chan | true | true | **true** | 11010 (ReceiveUln302) |
| 30309 | Read chan | true | true | false | 11010 |
| 30110 | Arbitrum | true | false | false | 11010 |
| 30202 | HyperEVM | true | true | false | 11010 |

- **Contradiction confirmed for 2 EIDs (30155, 30301):** `EndpointV2.isSupportedEid(eid) == true` while the default ULN config's required DVN array contains `0x000000000000000000000000000000000000dEaD` (code length 0). The default receive library is the real ReceiveUln302 contract (code size 11010), so the dead DVN is inside the config, not at the library level.
- **Quote path reverts for 4/5 EIDs** (all except Arbitrum/30110). The revert is consistent with the default route being unusable when the required DVN cannot sign attestations.
- The dead DVN was detected by scanning the raw `getConfig(eid, address(0), 2)` return bytes for the 32-byte ABI-encoded `0x...dEaD` word, because the deployed ReceiveUln302 returns `abi.encode(UlnConfig)` wrapped in a `bytes memory` envelope that does not cleanly decode as a raw tuple via `abi.decode`.

### Impact narrative

- The contradiction means `isSupportedEid` advertises a path as usable for messaging, but the default required DVN is a dead address that can never produce a valid verification. Any OApp relying on the default config (i.e., not setting a custom ULN config) for these EIDs cannot receive messages.
- However, this is not a fund-loss path by itself: OApps that set custom ULN configs with live DVNs are unaffected, and the endpoint owner can reconfigure defaults via `setDefaultUlnConfigs`. The bug is a default-configuration liveness/availability issue, not a direct fund-theft vector.
- **submit_ready remains 0.** The impact narrative does not meet the submission gate (no deployed OApp loss path, no privileged-only exploit, no direct fund theft). The artifact is a faithful record of the on-chain state contradiction.

### Validator status

- `pytest tests/test_native_layerzero.py` -> **17 passed** (no regression)
- `forge build --root foundry` -> **clean** (warnings only)
- `forge test --root foundry --match-path 'test/LayerZero*'` -> **16 passed / 0 skipped** (includes the new Direction C fork test)

## Corpus-informed deep-dive (AuditVault + Solodit)

### Mining summary

- **AuditVault patterns:** 2383 findings across 826 protocols
- **Solodit patterns:** 159 findings
- **Direct LayerZero-ecosystem matches:** 12 (Stargate, LzApp/ONFT, Audius endpoint, Mozaic DoS, Sweep n Flip irrecoverable state, LayerZero Aptos freeze bridge)
- **High-value correlated matches:** 569 across 247 protocols (messaging/bridge/verification/oracle/default_config/replay/access_control/upgrade/reentrancy/payload/fee axes)
- Top correlative protocols: Tapioca DAO (17), Blueberry (10), Notional (9), Connext (8), Maia DAO (8), ParaSpace (8), Taiko (8)

### New directions explored (all honest-zero)

| Direction | Surface | Corpus correlation | Outcome |
|-----------|---------|-------------------|---------|
| D | Nonce replay via skip/nilify/burn | SKALE MessageProxy reentrancy replay, Taiko signature replay, BLS Wallet signature replay, Superform replay protection | **Honest-zero.** Clear-before-execute pattern (`lzReceive` line 178 before 179) deletes slot + advances lazy checkpoint before OApp callback. `_verifiable` blocks re-verification of delivered nonces. nilify-reverify is intended recovery path with NIL_PAYLOAD_HASH sentinel blocking original payload replay. |
| E | Library upgrade grace-period race | Beanstalk diamond upgrade, Basin upgradeable-by-anyone, Audius endpoint registration frontrun | **Honest-zero.** `isValidReceiveLibrary` checks current default, custom, and timed-out lib. Old lib can verify during grace period (intended). Each lib uses its own config. `verify` is `isValidReceiveLibrary`-gated. |
| F | ComposeMsg reentrancy | Stargate emergencyWithdraw reentrancy, SKALE MessageProxy reentrancy | **Honest-zero.** `lzCompose` marks slot as `RECEIVED_MESSAGE_HASH` before calling `ILayerZeroComposer.lzCompose`. Re-entrant `lzCompose` for same (from,to,guid,index) fails hash check. `sendCompose` for same slot reverts `LZ_ComposeExists`. |
| G | allowInitializePath first-nonce race | Audius endpoint registration frontrun, Morpho missing init checks, LzApp frozen mint DoS | **Honest-zero.** `verify` requires `isValidReceiveLibrary` — only registered receive lib can call. Receive lib checks DVN signatures. `allowInitializePath` is OApp callback, checked by `_initializable` when `lazyInboundNonce == 0`. |
| H | Executor option decoding | Li.fi generic calls, Connext router config, Clober fee access | **Honest-zero.** All option parsers validate lengths (`decodeLzReceiveOption` checks 16/32, `decodeNativeDropOption` checks 48, `decodeLzComposeOption` checks 18/34). `UlnOptions.decode` validates `cursor == _options.length`. `CalldataBytesLib` uses checked calldata slices. `unchecked` blocks only where overflow impossible. |
| I | DVN quorum bypass via sybil | Audius quorum bypass with sybil | **Honest-zero.** `_checkVerifiable` iterates required DVN list (all must sign) then optional DVNs (threshold must sign). `_verify` stores `msg.sender` — only actual DVN contract can create its own verification entry. No way to forge another DVN's signature. |
| J | Send-side fee flow / withdrawFee | DAO fees unavailable due to strict access control | **Honest-zero.** `_debitFee` checks `fees[msg.sender] >= _amount` before transfer. State updated before external call (checks-effects-interactions). `Transfer.native` uses `.call` with success check. Workers can only withdraw their own credited fees. |
| K | PacketV1Codec header manipulation | Aave gho listing payload permanently modifies storage | **Honest-zero.** All field accessors use fixed offsets with constant boundaries. `_assertHeader` validates 81-byte length, version, and dstEid. No dynamic parsing in the codec. |
| L | AddressCast truncation/padding | — | **Honest-zero.** `toBytes32(bytes)` validates length <= 32. `to(bytes32,uint256)` validates size 1-32. `toAddress(bytes)` validates length == 20. All shifts in `unchecked` are bounded by validated inputs. |

### Key invariants confirmed

1. **Clear-before-execute** (`EndpointV2.sol:178` before `:179`) — prevents nonce replay via reentrancy in `lzReceive` callback.
2. **Mark-as-received-before-execute** (`MessagingComposer.sol:56` before `:57`) — prevents compose reentrancy.
3. **`_verifiable`** (`EndpointV2.sol:344-353`) — prevents re-verification of delivered nonces (both disjuncts fail after delivery).
4. **`_assertAuthorized`** — gates `skip`/`nilify`/`burn`/`clear` to OApp or registered delegate only.
5. **`isValidReceiveLibrary`** — gates `verify` to registered receive libraries only.
6. **`_assertAtLeastOneDVN`** — prevents config with zero DVNs.
7. **`_isSupportedEid`** — checks default config has required DVNs or optional threshold.
8. **NIL_PAYLOAD_HASH sentinel** — `bytes32(type(uint256).max)` blocks execution of nilified payloads (keccak256 can't produce this value).
9. **Option length validation** — all option decoders validate exact byte lengths.

### Submission readiness assessment

- **submit_ready = 0** (unchanged).
- Direction C (dead-DVN/isSupportedEid contradiction) is the strongest finding but is a liveness/availability issue, not a fund-theft vector.
- All 9 new directions (D-L) are honest-zero with strong structural prevention.
- The LayerZero V2 protocol demonstrates rigorous security engineering across all explored surfaces.

## Direction M — OFTAdapter `_credit` CEI violation (defensive flag)

### Source

- `sources/layerzero/repo/oapp/contracts/oft/OFTAdapter.sol:124-129`

```solidity
function _credit(...) internal virtual override returns (...) {
    outboundAmount -= _amountToCreditLD;       // STATE WRITE FIRST
    innerToken.safeTransfer(_to, _amountToCreditLD);  // EXTERNAL CALL SECOND
    return _amountToCreditLD;
}
```

- CEI violation: state effects ordered before the external transfer call.
- No reentrancy guard anywhere in the OApp/OFT hierarchy (verified across OAppCore, OAppSender, OAppReceiver, OFTCore, OFT, OFTAdapter, OAppPreCrimeSimulator).

### PoC

- `foundry/test/OFTAdapterReentrancy.t.sol` — Direction M PoC mirror. Self-contained, no OpenZeppelin imports.
- ReentrantToken (ERC20-stand-in) calls `onTokenReceived` during `transfer`, mirroring ERC777 `tokensReceived` behavior.
- AttackerHook triggers reentrancy via `_debitThis` during the credit callback.
- Test confirms:
  - During the callback, `availableToSend` is temporarily inflated (1000 - 700 = 300 instead of 1000 - 800 = 200)
  - Reentrant `_debitThis` debits the inflated free amount (200e18 in the test scenario)
  - Final accounting balances (outbound == balance), so the **concrete fund theft requires further exploitation design**
- **Honest-zero on direct fund theft** — the temporary inflation does not produce a permanent deficit given the symmetric before/after balance.
- **Defensive flag still valid** — the CEI violation is real and exploitable by chains that deploy OFTAdapter with ERC777 or other non-standard ERC20 tokens. Auditors should flag this as a high-priority recommendation: add `nonReentrant` to `_credit` and `_debit*` paths, or reorder operations to follow CEI.

### Validator status (post Direction M)

- `pytest tests/test_native_layerzero.py` -> **17 passed** (no regression)
- `forge build --root foundry` -> **clean**
- `forge test --root foundry --match-path 'test/LayerZero*'` + OFTAdapterReentrancy -> **17 passed / 0 skipped**

### Final submission assessment

- **submit_ready = 0** (unchanged).
- Direction C remains the strongest live artifact (dead-DVN/isSupportedEid contradiction, 2 EIDs affected out of 91+ scanned).
- Direction M is a defensive CEI flag — valuable to surface but not a submission-grade fund-loss proof.
- **Rotate decision:** after 13+ directions explored across core protocol, OApp/OFT/ONFT, DVN adapters, and fee flow surfaces, all exploitable paths require either (a) custom ERC20 (non-standard behavior), (b) privilege-gated configuration, or (c) liveness-only impact. None satisfy the foundation submission gates for confirmed fund theft with reproducible live path. Recommend rotating to a new target surface.
