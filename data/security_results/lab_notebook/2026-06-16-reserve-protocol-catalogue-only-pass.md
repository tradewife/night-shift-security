# Lab entry — Reserve Protocol catalogue-only pass

- date: 2026-06-16
- operator mode: autonomous orchestrator
- target: Reserve Protocol
- config: `src/night_shift_security/config/reserve_protocol_cantina.json`

## Command

```bash
set -a && source .env && set +a
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/reserve_protocol_cantina.json \
  bounty loop --target reserve-protocol --iterations 1 --trials 1
```

## Result

The run completed with live RPC/fork validation:

- `fork_confirmed=53/53`
- `fork_reproduced=57`
- findings: 24
- Immunefi research packs: 2
- `submit_candidates=[]`
- best recommendation: `polish_validator`

The strongest findings were governance-capture candidates:

- `NSS-0014`: evidence grade 4, `catalog_analogue=true`, `qualifies=false`
- `NSS-0015`: evidence grade 4, `catalog_analogue=true`, `qualifies=false`

The loop applied:

- `saturate_slug:reserve-protocol`
- `queue_refinement:reserve-protocol/governance_capture`
- `queue_refinement:reserve-protocol/treasury_drain`
- `config_fallback:reserve-protocol` with `hint=novel_or_shoestring`

## Decision

No submission candidate. The current Reserve Protocol config is producing Beanstalk-style governance/treasury analogues with fork reproduction but no novelty.

Do not rerun this config without a novel target-specific proposal, source-derived governance module mapping, or a concrete live-contract state delta that separates it from catalogue governance capture.
