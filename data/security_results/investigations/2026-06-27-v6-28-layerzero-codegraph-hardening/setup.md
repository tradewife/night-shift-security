# Setup — v6.28 LayerZero codegraph hardening

- Repo root: `/home/kt/.local/share/warp-terminal/worktrees/night-shift-security/spire-tepui`
- Pinned LayerZero clone: `sources/layerzero/repo`
- Source commit: `0990059e3ee61ea95f45011cf7284243531fb4c3`
- `codegraph` installed via `npm i -g @colbymchenry/codegraph`
- `codegraph init` run against `sources/layerzero/repo`
- Upstream LayerZero workspace dependencies installed with `corepack yarn install`

## Validation plan

1. Root NSS sidecar checks:
   - `PYTHONPATH=src python3 -m pytest tests/test_native_layerzero.py`
   - `forge build --root foundry`
   - `forge test --root foundry --match-path test/LayerZero*.sol`
2. Upstream local-only hardening checks:
   - `cd sources/layerzero/repo/protocol && forge test --match-path test/EndpointV2CodegraphHardening.t.sol`
   - `cd sources/layerzero/repo/messagelib && forge test --match-path test/ReceiveUln302CodegraphHardening.t.sol`
