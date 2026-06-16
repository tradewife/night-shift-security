# Lab entry — Solodit authenticated agent proposal lane

- profile: `nightsoul`
- cron job: `nss-solodit-agent-proposals` (`d80d0f18d5b7`)
- run time: 2026-06-16 20:34 Australia/Sydney
- provider: `xai-oauth`
- model: `grok-4.3`

## Result

The authenticated Hermes cron lane ran successfully after manual trigger:

- Hermes cron status recorded last run `ok`.
- Agent log showed credential pool load for `xai-oauth`.
- Agent log showed 7 model API calls against `grok-4.3`.
- Output artifact: `data/security_results/hermes_proposals/solodit-20260616.json`.
- `latest.json` was updated for next deterministic ingestion.

The first agent-written proposal sidecar used an invalid Wormhole config path and empty parameters. Corrected the ignored proposal artifacts to match NSS validation:

- `required_config`: `src/night_shift_security/config/wormhole_triage.json`
- supported templates only: `access_control_escalation`, `composability_risk`
- proposal metadata remains `trusted=false`
- accepted by deterministic loader: 3 access-control proposals, 5 composability proposals

## Smoke validation

Ran:

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/wormhole_triage.json \
  --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --target wormhole --iterations 1 --trials 1
```

Observed:

- `proposal_target_match=true`
- target: `wormhole`
- findings: 13
- submit candidates: 0
- best recommendation: `hold`
- quick smoke RPC status: `rpc_ready=false`

## Notes

- This proves the fully authenticated LLM agent lane is functional and can write proposal sidecars for deterministic ingestion.
- The proposal sidecar is intentionally untrusted and cannot bypass NSS validation, evidence grading, or submission gates.
- `failure_signatures.jsonl` was absent during the agent run; Hermes skipped it and continued.
