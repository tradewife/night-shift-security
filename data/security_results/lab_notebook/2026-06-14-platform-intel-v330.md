# Lab — SPEC v3.3.0 Platform Intel + Submittable Export

**Date:** 2026-06-14  
**SPEC:** v3.3.0  
**Tests:** 344 passed, 3 skipped

## Platform sync

```bash
.venv/bin/python -m night_shift_security.cli.main platform sync --all
.venv/bin/python -m night_shift_security.cli.main platform diff
```

| Platform | Live | Curated | Coverage |
|----------|------|---------|----------|
| Immunefi | 208 | 18 | ~8.7% Tier-A (by design) |
| Cantina | 52 | 12 | ~23% Tier-A |

Artifacts: `data/security_results/platform/*.json`

## Export gate

- `bounty/research/` — grade ≥ 3, triage surface, catalogue analogues OK
- `bounty/submittable/` — **empty** until `qualifies_for_submission()` (unchanged P0)
- Wormhole grade-4 triage → `export_track: research_surface` only

## Harness alignment

| Slug | Config |
|------|--------|
| coinbase | `coinbase_cantina.json` (nomad fork) |
| polymarket | `polymarket_cantina.json` (polygon nomad analogue) |
| reserve-protocol | `reserve_protocol_cantina.json` (beanstalk pattern) |

## Next (P0 unchanged)

- KLend real instruction discriminators → `live_executed` balance delta
- Novel Wormhole exploit with economic delta (surface ≠ Immunefi report)