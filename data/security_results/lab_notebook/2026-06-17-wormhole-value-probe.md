# 2026-06-17 - Wormhole live value probe

## Context

The previous Wormhole iteration separated triage-only/no-delta evidence from catalogue replay and routed it to `missing_economic_impact -> generate_value_moving_poc`. The next step was to bind the token bridge to live deployed accounting instead of governance getters.

## Change

- Added `foundry/test/WormholeValueProbe.t.sol`.
- The probe forks Ethereum mainnet, reads live Wormhole Token Bridge USDC balance and `outstandingBridged(USDC)`, then attempts malformed `completeTransfer` as an attacker.
- The assertion is intentionally value/accounting based: bridge USDC balance, attacker USDC balance, and outstanding USDC accounting must remain unchanged.
- Added `wormhole-token-bridge-value-probe-ethereum` to fork targets and Wormhole configs.
- Added `WORMHOLE_VALUE_PROBE` fork confirmation so the runner records the probe, while the task verifier still downgrades zero-delta output to `missing_economic_impact`.

## Verification

```text
.venv/bin/python -m pytest tests/test_fork.py tests/test_failure_trace_rsi.py tests/test_task_verifier.py tests/test_wormhole_economic.py -q
29 passed

.venv/bin/python -m pytest
405 passed, 5 skipped

set -a && source ../.env && set +a; forge test --match-path test/WormholeValueProbe.t.sol -vv
1 passed
TOKEN_DELTA:0
DELTA_WEI:0
BRIDGE_ACCOUNTING_VIOLATION:0
```

## Result

No submit-ready bug. The malformed VAA path is correctly blocked on live state. Next Wormhole work should generate signed-message/accounting-differential cases for `completeTransfer*`, `createWrapped`, and wrapped/native accounting rather than repeating malformed input probes.
