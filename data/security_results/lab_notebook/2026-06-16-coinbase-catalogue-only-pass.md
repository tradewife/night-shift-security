# Lab entry — Coinbase catalogue-only pass

- date: 2026-06-16
- operator mode: autonomous orchestrator
- target: Coinbase
- config: `src/night_shift_security/config/coinbase_cantina.json`

## Command

```bash
set -a && source .env && set +a
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/coinbase_cantina.json \
  bounty loop --target coinbase --iterations 1 --trials 1
```

## Result

The run completed with live RPC/fork validation:

- `fork_confirmed=39/39`
- `fork_reproduced=43`
- findings: 23
- Immunefi research packs: 0
- `submit_candidates=[]`
- best recommendation: `hold`
- CPCV: `SAFE=0`, `DANGER=4`, average PBO `100%`

All scored findings were `catalog_analogue=true` and evidence grade 1. The top family was Nomad-style access-control escalation; it does not separate from catalogue bridge/admin analogues.

The loop applied:

- `saturate_slug:coinbase`
- `queue_refinement:coinbase/access_control_escalation`
- `queue_refinement:coinbase/treasury_drain`
- `config_fallback:coinbase` with `hint=novel_or_shoestring`

## Decision

No submission candidate. The current Coinbase config should not be rerun without a novel, Coinbase-specific target model or source-derived live surface.
