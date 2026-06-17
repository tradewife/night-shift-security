# Lab entry — v5 pivot, audit + NativeHarness substrate gate

- wall_time_s: ~600 (audit + edits + tests)
- spec: v5.0.0-draft
- audit: SYSTEM_AUDIT_2026-06-18.md

## Why

v4.2.0 produced 0 submissions across every full HIPIF run. The 2026-06-18 audit
identified eight structural defects upstream of the gates and one wrong goal
model (catalogue-replay engine labelled as adversarial research). The gates,
trust boundary, RSI, lab-notebook, and skill lockdown layers were correctly
implemented and remain authoritative. The discovery substrate must pivot.

## Pivot decision

- Stop running the legacy chain via a bash precondition gate.
- Mark each in-scope target with a NativeHarness status and refuse the
  legacy chain until at least one reaches `ready`.

## Shipped

| Item | Path | Result |
|------|------|--------|
| Audit report | `SYSTEM_AUDIT_2026-06-18.md` | Created. |
| SPEC v5 pivot header | `SPEC.md` | `5.0.0-draft` + new §0/"Why this version exists" |
| AUDIT v4.2 closure | `AUDIT.md` | Reference + v5 Pivot section |
| Cron precondition | `hermes/scripts/nss-hipif-chain.sh` | `NSS_HIPIF_PAUSE_FOR_NATIVE=1` defaults to paused; manual exit code 0, no_run marker manifest |
| Native module | `src/night_shift_security/native/__init__.py` | Manifest schema + upsert + read |
| Native CLI | `cli/main.py` | `native status`, `native mark` subcommands |
| Native tests | `tests/test_native_harness.py` | 6 passed |
| Cron YAML comment | `hermes/cron/jobs.example.yaml` | v5 reference |
| First target | uniswap_v4 | `native mark --status mapped` only — ABI/IDL/source still required |

## Verification

```
.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q
444 passed, 5 skipped (was 438 passed → +6 net new)
```

Native CLI smoke:
```
$ .venv/bin/python -m night_shift_security.cli.main native status
{ "ready_count": 0, "reason": "paused_awaiting_native_harness", ... }

$ NSS_HIPIF_PAUSE_FOR_NATIVE=1 bash hermes/scripts/nss-hipif-chain.sh
NSS_HIPIF_PAUSE_FOR_NATIVE=1 and no native harness ready (...missing or empty).
Pausing cron until at least one NativeHarness target reaches status=ready.
```

After `native mark --slug uniswap_v4 --status mapped` (not `ready`) the manifest
records `ready_count=0`; once a target reaches `ready`, the cron releases the
precondition gate without operator intervention.

## Out of scope this lab session

- Building the actual Uniswap v4 ABI harness (C1 from audit)
- Implementing the `MeasuredImpactOracle` (C2)
- Saturating `pick_next_target` with the new harness precondition (C3)
- Splitting fork_reproduced aggregator labels (C7)

These are next steps; they require roughly 3–5 days for C1 plus 0.5–1 day each
for C2/C3/C7 and ship as v5.0.0.
