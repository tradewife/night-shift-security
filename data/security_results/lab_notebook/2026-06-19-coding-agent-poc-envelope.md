# Lab entry — coding-agent PoC envelope wiring (B5→B8)

## Trigger
- coding-agent outer loop — continue B5_NO_CANDIDATE_POC substrate
- commands: `pytest tests/test_benchmarks.py tests/test_pocgen.py tests/test_bounty_loop.py`

## State before
- native ready count: 7 (kamino + 4 Solana + 2 EVM)
- top Kamino survivor: `kamino-native-001` (`refresh_reserve`, discriminator `0x02da8aeb4fc91966`)
- submit_ready: false
- blocker: PoC artifacts existed but were not attached to finding `parameters.candidate` during pipeline export

## Change made
- files:
  - `src/night_shift_security/pocgen/envelope.py` — build v4 envelope + `attach_poc_envelope` / `enrich_concrete_sequence_candidates`
  - `src/night_shift_security/core/pipeline.py` — enrich concrete_sequence survivors before dedupe/export
  - `tests/test_pocgen.py` — envelope attach + measured-impact gate rejection tests
- rationale: bounty loop / submission gates read `parameters.candidate`; PoC path must flow from `poc generate` without gate edits.

## Validation
- tests: `pytest tests/test_benchmarks.py tests/test_pocgen.py tests/test_bounty_loop.py` — 44 passed
- benchmark: unchanged harness, green
- deterministic NSS: not run (code-only substrate change)

## Gate result
- submit_ready: false (expected — impact still fail-closed; envelope present but `impact_oracle.measured=false`)
- gates: unchanged; `_v4_candidate_submission_ok` correctly rejects envelope without measured delta

## Next action
- Run Kamino depth pass with `use_concrete_sequences` and validator replay for `kamino-native-001`; hunt non-fee measured delta on `refresh_reserve` path with fresh Scope oracle strategy.