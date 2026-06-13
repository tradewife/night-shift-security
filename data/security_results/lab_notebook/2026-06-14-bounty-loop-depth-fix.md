# Lab entry — bounty-loop fork depth fix

## Trigger
Day Shift: user reported cron completing in ~1s (not credible depth).

## Root cause
- Pendle (Cantina/EVM) inherited `kamino_klend.json` via wrong `_CONFIG_OVERRIDES` mapping.
- `kamino_klend.json` has `fork_validation.top_n: 0`; EVM branch enabled forks but did not raise `top_n`.
- Result: `Fork confirmed: 0/0`, ~1s runs with 36 catalogue findings but zero fork reproduction.

## Fix (SPEC v3.0.9)
- `pendle` (+ other Cantina slugs) → `euler_cantina.json`.
- `build_loop_config`: when EVM + RPC ready, set `fork_validation.top_n` to at least 3.
- Cron: `NSS_LOOP_DEPTH_SLUG` Mon=wormhole, Thu=kamino (bypass saturated list).
- Cron lab notebook: add missing `import os` for depth_pass field.

## Verification
- `tests/test_bounty_loop.py`: +3 tests (pendle config, EVM top_n from klend base, depth slug).
- Full suite: 309 passed, 3 skipped.
- Pendle smoke: `resolve_pipeline_config_path` → `euler_cantina.json`, `top_n: 3`.

## Expected runtime (post-fix)
- Cantina/EVM with RPC: scan + fork top_n=3 → typically 2–5+ minutes (Morpho reference ~154s).
- Solana depth (Thu kamino): validator clone + CPI probes → minutes when `SOLANA_MAINNET_RPC_URL` set.

## Open
- Jun 14 04:00 cron tick missed (scheduler); manual catch-up ran fast pre-fix.
- No `submit_ready` candidates; human gate unchanged.