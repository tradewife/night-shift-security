# 2026-06-17 - Wormhole live value probe

## Context

The previous Wormhole iteration separated triage-only/no-delta evidence from catalogue replay and routed it to `missing_economic_impact -> generate_value_moving_poc`. The next step was to bind the token bridge to live deployed accounting instead of governance getters.

## Change

- Added `foundry/test/WormholeValueProbe.t.sol`.
- The probe forks Ethereum mainnet, reads live Wormhole Token Bridge USDC balance and `outstandingBridged(USDC)`, then attempts malformed `completeTransfer` as an attacker.
- The assertion is intentionally value/accounting based: bridge USDC balance, attacker USDC balance, and outstanding USDC accounting must remain unchanged.
- Added `wormhole-token-bridge-value-probe-ethereum` to fork targets and Wormhole configs.
- Added `WORMHOLE_VALUE_PROBE` fork confirmation so the runner records the probe, while the task verifier still downgrades zero-delta output to `missing_economic_impact`.
- Added a mocked-authorized signed-message baseline that returns a registered-emitter VM from the fork-local mocked core verifier. It moves exactly 1 USDC from the deployed bridge to the attacker and reduces `outstandingBridged(USDC)` by exactly 1 USDC.
- Added `HARNESS_AUTH_MOCKED=1` as a hard non-submittable marker; Wormhole economic gates reject mocked authorization even when token delta is positive.
- Added Wormholescan signed-VAA fetch/decode helpers and an optional real signed VAA replay path. The current selected Ethereum-native release VAA is `1/ec7372995d5cc8732397fb0ad35c0121e0eaa90d26f828a534cab54391b3a4f5/1402175`; it verifies through the live core and is already completed on Ethereum, producing zero delta.
- Added `AUTHORIZED_REPLAY=1` as a non-submittable marker unless a bridge accounting violation is also proven.
- Added real VAA corpus classification and runtime report generation. Latest live scan over 100 operations decoded 12 token-bridge VAAs: 11 foreign wrapped mints and 1 Ethereum-native lock-out; no Ethereum-native release candidate was present in the latest 100 operations.
- Added optional replay lanes for Ethereum wrapped-mint `completeTransfer` and asset-meta `createWrapped` VAAs. Latest live corpus page has no matching Ethereum wrapped-mint or asset-meta VAA, so these routes skip until matching real signed VAAs are available.
- Added documented Wormholescan `page`/`pageSize` pagination and route fixture writers for native release, wrapped mint, and asset metadata VAAs.
- Deep scan over 40 pages found real replay fixtures:
  - native release: `1/ec7372995d5cc8732397fb0ad35c0121e0eaa90d26f828a534cab54391b3a4f5/1402175`
  - Ethereum wrapped mint: `15/148410499d3fcda4dcfd68a1ebfcdddda16ab28326448d4aae4d2f0465cdfcb7/8343`
  - asset metadata: `2/0000000000000000000000003ee18b2214aff97000d974cf647e7c347e8fa585/654809`
- Real native-release and wrapped-mint replays both verify through live core but are already completed on Ethereum, producing zero token delta and `BRIDGE_ACCOUNTING_VIOLATION:0`.
- The asset metadata fixture is same-chain Ethereum metadata (`tokenChain == bridge.chainId()`), so the createWrapped replay now skips before registered-emitter assertions; same-chain metadata is not a viable createWrapped target on Ethereum.
- A pending plain payload-id 1 Ethereum-native release fixture (`1/ec7372995d5cc8732397fb0ad35c0121e0eaa90d26f828a534cab54391b3a4f5/1402169`) completed on fork. The harness initially assumed 18-decimal denormalization and failed; after switching native-release expected delta to live token decimals, bridge delta, recipient delta, and outstanding delta matched. This is authorized replay only.

## Verification

```text
.venv/bin/python -m pytest tests/test_wormholescan.py tests/test_fork.py tests/test_failure_trace_rsi.py tests/test_task_verifier.py tests/test_wormhole_economic.py -q
40 passed

.venv/bin/python -m pytest
416 passed, 5 skipped

set -a && source ../.env && set +a; forge test --match-path test/WormholeValueProbe.t.sol -vv
2 passed, 3 optional route replays skipped

set -a && source ../.env && set +a; export WORMHOLE_REAL_VAA_HEX=$(cd .. && .venv/bin/python - <<'PY'
from night_shift_security.bridge.wormholescan import fetch_operations, select_eth_native_release_vaa
selected = select_eth_native_release_vaa(fetch_operations(limit=100))
print(selected["decoded"]["raw_hex"] if selected else "")
PY
); forge test --match-path test/WormholeValueProbe.t.sol -vv
3 passed
TOKEN_DELTA:0
DELTA_WEI:0
BRIDGE_ACCOUNTING_VIOLATION:0
HARNESS_AUTH_MOCKED:1
TOKEN_DELTA:1000000
REAL_SIGNED_VAA:1
AUTHORIZED_REPLAY:1

.venv/bin/python - <<'PY'
from night_shift_security.bridge.wormholescan import write_real_vaa_corpus_report
print(write_real_vaa_corpus_report(limit=100))
PY
decoded_token_bridge_vaas=12
route_counts={'foreign_wrapped_mint': 12}

.venv/bin/python - <<'PY'
from night_shift_security.bridge.wormholescan import fetch_operation_pages, build_real_vaa_corpus_report
ops = fetch_operation_pages(pages=40, page_size=100)
report = build_real_vaa_corpus_report(ops)
print(len(ops), report["decoded_token_bridge_vaas"], report["route_counts"])
PY
3994 718 {'foreign_wrapped_mint': 329, 'eth_native_release': 146, 'eth_native_lock_out': 119, 'eth_native_release_with_payload': 33, 'eth_native_lock_out_with_payload': 38, 'eth_wrapped_mint': 46, 'eth_wrapped_mint_with_payload': 6, 'asset_meta': 1}

set -a && source ../.env && set +a; \
export WORMHOLE_REAL_VAA_HEX=$(jq -r '.decoded.raw_hex' ../data/security_results/wormhole/real_vaas/latest_eth_native_release.json); \
export WORMHOLE_REAL_WRAPPED_VAA_HEX=$(jq -r '.decoded.raw_hex' ../data/security_results/wormhole/real_vaas/latest_eth_wrapped_mint.json); \
unset WORMHOLE_REAL_ASSET_META_VAA_HEX; \
forge test --match-path test/WormholeValueProbe.t.sol --match-test 'testForkWormholeReal(SignedVaa|WrappedMint)' -vv
2 passed
WORMHOLE_REAL_VAA_REPLAY:already_completed
WORMHOLE_WRAPPED_VAA_REPLAY:already_completed
TOKEN_DELTA:0
BRIDGE_ACCOUNTING_VIOLATION:0

set -a && source ../.env && set +a; \
export WORMHOLE_REAL_ASSET_META_VAA_HEX=$(jq -r '.decoded.raw_hex' ../data/security_results/wormhole/real_vaas/latest_asset_meta.json); \
forge test --match-path test/WormholeValueProbe.t.sol --match-test testForkWormholeRealAssetMetaCreateWrappedDifferential -vv
1 skipped
WORMHOLE_ASSET_META_REPLAY:same_chain_metadata

set -a && source ../.env && set +a; \
export WORMHOLE_REAL_VAA_HEX=$(jq -r '.decoded.raw_hex' ../data/security_results/wormhole/real_vaas/uncompleted_plain_eth_native_release.json); \
forge test --match-path test/WormholeValueProbe.t.sol --match-test testForkWormholeRealSignedVaaAccountingDifferential -vv
1 passed
WORMHOLE_REAL_VAA_REPLAY:completed_on_fork
TOKEN_DELTA:308414387625
OUTSTANDING_USDC_DELTA:308414387625
BRIDGE_ACCOUNTING_VIOLATION:0
```

## Result

No submit-ready bug. The malformed VAA path is correctly blocked on live state, the mocked-authorized path proves the deployed accounting baseline, real signed native-release and wrapped-mint VAAs are already completed with zero delta, pending plain native-release replay completes with matched accounting, and same-chain Ethereum asset metadata is not a createWrapped target. A pending Ethereum-targeted payload-id 3 candidate reverted with `invalid sender` on the standard `completeTransfer` lane, so transfer-with-payload messages are now split out and not treated as standard replay candidates. Next work should distinguish true token-bridge emitters from token-bridge-shaped payloads and investigate amount-mismatch rows only after emitter/protocol validation.
