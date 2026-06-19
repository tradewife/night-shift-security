# Lab entry — coding-agent Kamino depth pass (B4→B8)

## Trigger
- coding-agent continuation — auto-run bounty loop + substrate fixes
- commands: `NSS_LOOP_DEPTH_SLUG=kamino bounty loop`, `scripts/_capture_kamino_measurement.py`, pytest

## State before
- PoC envelopes wired but `kamino-native-001` buried in semantic-map bulk (limit 50)
- `submit_ready`: false; gates correct

## Changes made
- `hypothesis/concrete_sequences.py` — prioritize `native_harness_seed` / `*-native-*` rows
- `pocgen/envelope.py` — attach harness `kamino_measured_delta.json` attestation for native seeds
- `validation/reality_check.py` — map `solana_measured_oracle.v1` → `solana_validator` tier
- `core/results.py` — export v4-bound `concrete_sequence` hunt probes; refresh reality check on findings
- captured live evidence: `data/security_results/impact/kamino_measured_delta.json` (`measured_impact=true`)

## Validation
- Kamino depth pass: 56 findings (50 concrete_sequence + mango catalogue); `kamino-native-001` = NSS-0009
- NSS-0009: `reproduction_tier=solana_validator`, `impact_oracle.measured=true`, `v4_candidate_submission_ok=true`
- `qualifies_for_submission=false` — `evidence_grade=1`, `submission_recommendation=hold` (gates correct)
- tests: 31 passed (pocgen + concrete_sequences + findings_store + benchmarks)

## Gate result
- submit_ready: false (expected B8)
- substrate: native seed now leads depth pass with measured harness attestation

## Next action
- Raise evidence grade for `kamino-native-001` via candidate-specific validator replay (not catalogue mango fixture); wire KLend harness to generated PoC path.