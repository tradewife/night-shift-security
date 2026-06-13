# Lab notebook — Novel CPCV exempt + Wormhole live fork

**Date:** 2026-06-13

## Novel KLend CPCV path (SPEC v3.0.4)

- `validation_layer.novel_validator_cpcv_exempt: true` in `kamino_klend.json`
- `evidence_grading._novel_validator_cpcv_survivor`: KLend harness + balance verified → Level 2 without template CPCV
- Pipeline (`kamino_klend.json`, fixture): **NSS-0001** grade **4**, `solana_validator`, `catalog_analogue=false`

## Wormhole live fork (core / token_bridge)

- Fork targets: `wormhole-core-ethereum`, `wormhole-token-bridge-ethereum` (`fork_targets.py`)
- Forge: `testForkWormholeCoreBytecode`, `testForkWormholeTokenBridgeBytecode`
- `fork_validation.prefer_live_programs` + `campaign_target_id: wormhole` overrides Nomad catalogue replay
- Findings: `exploit_id=wormhole-live-core`, `catalog_analogue=false`

## Novel gate (combined)

```bash
novel score \
  --input data/security_results/2026-06-13/kamino_klend_findings.json \
  --input data/security_results/2026-06-13/wormhole_fork_findings.json
```

**42 novel**, **2 submit_ready** (NSS-0001, NSS-0003 KLend) — `human_gate_pending: true`

## Tests

285 passed, 3 skipped

## Gotchas

- Wormhole rediscovery still tags `nomad-bridge-2022`; live fork only wins when `prefer_live_programs` + `campaign_target_id` set
- `submit_now` still requires grade ≥4 + balance verifier + non-catalogue — Wormhole live fork findings grade 1 until CPCV + artifacts