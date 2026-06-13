# Lab notebook — Phase D + Wormhole Block B

**Date:** 2026-06-13  
**Session:** Day Shift — operator impact + Wormhole program mapping

## Shipped

### Phase D (SPEC v3.0.3)
- `impact/oracle_arbitrage.py` — oracle vs Uniswap-V2 spot on fork
- `impact/tvs_maximization.py` — sibling pool ranking post-PoC
- CLI: `impact oracle`, `impact tvs`
- Hermes skill: `operator-triage`
- Template: `config/wormhole_siblings.json`

### Wormhole Block B
- `triage/wormhole_program_map.py` — canonical mainnet IDs + repo scan
- `sources/wormhole/recon.json` — core/token_bridge EVM+Solana (not Nomad proxy)
- `data/security_results/triage/wormhole_program_map.json`
- `targets/wormhole.json` metadata updated with live program IDs
- Day Shift `current.md` Block B checked

## Canonical programs (mainnet)

| Component | Ethereum | Solana |
|-----------|----------|--------|
| Core | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | `worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth` |
| Token Bridge | `0x3ee18B2214AFF97000D974cf647E7C347E8fa585` | `wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb` |

## Tests

274 passed, 5 skipped (+10 new: impact, wormhole map, recon)

## Open questions

- Clone wormhole monorepo for `triage files` + `wormhole-map --repo` discovery pass
- Novel PoC still blocked on catalogue analogue gate — Kate human gate unchanged
- Block C (score novel candidates) still open in Day Shift plan

## Gotchas

- Nomad analogue in `exploit_id` is validation-only; novel work targets `programs` in recon
- TVS sweep uses balance/totalSupply proxy — not full DeFiLlama TVL
- Oracle getter signatures vary per feed; confirm ABI on fork before `impact oracle`