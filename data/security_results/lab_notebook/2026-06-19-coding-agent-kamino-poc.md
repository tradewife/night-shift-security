# Lab entry — coding-agent Kamino PoC (B5)

## Trigger
- coding-agent outer loop — bottleneck B5_NO_CANDIDATE_POC
- commands: `pytest tests/test_benchmarks.py tests/test_pocgen.py`

## State before
- native ready count: 7 (kamino ready with `kamino_measured_delta.json`)
- top Kamino survivor: `kamino-native-001` (`refresh_reserve`, discriminator `0x02da8aeb4fc91966`)
- submit_ready: false
- blocker: candidate-specific PoC artifacts were fail-closed stubs without harness account bindings

## Change made
- files:
  - `src/night_shift_security/pocgen/kamino_bindings.py` — resolve KLend program/market/reserve + source commit
  - `src/night_shift_security/pocgen/generator.py` — Kamino path writes bindings + manifest + reproduction_artifact
  - `tests/test_pocgen.py` — Kamino binding, fee-only reject, catalog≠novel tests
  - `docs/agents/coding-agent-orchestrator-loop.md` — outer loop doc (not Hermes cron)
  - removed `nss-hermes-prime-bootstrap` from `hermes/cron/jobs.example.yaml`
- rationale: B5 requires PoC paths bound to real candidates; impact proof remains fail-closed until measured non-fee delta.

## Validation
- tests: `pytest tests/test_benchmarks.py tests/test_pocgen.py`
- benchmark: unchanged harness, must stay green
- deterministic NSS: not run (code-only substrate change)

## Gate result
- submit_ready: false (expected — PoC still fail-closed on impact)
- gates: unchanged

## Next action
- Wire `poc generate` output into bounty loop candidate envelope for `kamino-native-001`; hunt measured delta on validator replay.