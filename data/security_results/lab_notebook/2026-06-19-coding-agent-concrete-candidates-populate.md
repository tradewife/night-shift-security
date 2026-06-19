# Lab entry — coding-agent concrete candidates population (B3→G3)

## Trigger
- coding-agent orchestrator loop — bottleneck B3_NO_CONCRETE_BIND
- commands: `semantic candidates --slug <target> --store concrete_candidates.jsonl`

## State before
- `concrete_candidates.jsonl`: empty (0 rows)
- `ready_count=7` (kamino, jito, raydium, orca, uniswap_v4, aave_v3, morpho_blue)
- Semantic artifacts existed for 5/7 targets; aave_v3 and morpho lacked semantic dirs
- G3 unmet: "every ready target has ≥50 rows in concrete_candidates.jsonl"

## Changes made
- `semantic map --slug aave_v3 --repo sources/aave_v3/repo --store concrete_candidates.jsonl` — created semantic artifacts + 716 candidates
- `semantic map --slug morpho --repo sources/morpho/repo --store concrete_candidates.jsonl` — created semantic artifacts + 110 candidates
- `semantic candidates --slug kamino/jito/raydium/orca/uniswap_v4 --store concrete_candidates.jsonl` — upserted from existing seeds
- `tests/test_pipeline.py` — added `concrete_sequence` to expected template set (new template was imported via `core/pipeline.py` but not in test)

## Validation
- Per-target counts: aave_v3=716, kamino=666, jito=513, orca=465, raydium=229, morpho=110, uniswap_v4=66 (all ≥50)
- Total: 2765 candidates
- Tests: 711 passed, 7 skipped (was 710 passed + 1 failed; fix: added `concrete_sequence` to template set)
- Kamino bounty depth pass: 41 findings generated, all catalogue-based (expected saturation without live RPC)

## Gate result
- submit_ready: false (expected — catalogue replay, no measured economic delta)
- G3: **met** — all 7 ready targets have ≥50 candidates

## Next action
- Wire live RPC for kamino measured delta (Phase 8); promote findings past catalogue saturation via candidate-specific validator replay.
