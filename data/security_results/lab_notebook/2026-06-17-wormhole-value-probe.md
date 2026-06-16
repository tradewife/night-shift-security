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

## Verification

```text
.venv/bin/python -m pytest tests/test_wormholescan.py tests/test_fork.py tests/test_failure_trace_rsi.py tests/test_task_verifier.py tests/test_wormhole_economic.py -q
31 passed

.venv/bin/python -m pytest
407 passed, 5 skipped

set -a && source ../.env && set +a; forge test --match-path test/WormholeValueProbe.t.sol -vv
2 passed, 1 skipped

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
```

## Result

No submit-ready bug. The malformed VAA path is correctly blocked on live state, the mocked-authorized path proves the deployed accounting baseline, and the real signed VAA path proves legitimate replay is already completed with zero delta. Next Wormhole work should search for non-mocked bridge accounting violations, not authorized replay.
