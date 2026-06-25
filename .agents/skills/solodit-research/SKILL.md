---
name: solodit-research
description: Use after the deterministic NSS HIPIF chain to mine Cyfrin Solodit findings and local Solodit pattern artifacts for untrusted, target-pinned Hermes proposal JSON. Use when creating Solodit-informed attack hypotheses, analogue research digests, or next-run proposal files from data/security_results/knowledge/solodit_patterns.jsonl.
---

# Solodit Research

Use Solodit as historical analogue intelligence only. Never treat a Solodit match as evidence for `submit_ready`, evidence grade, deployed viability, or credible reproduction.

## Inputs

Read, in order:

1. `data/security_results/hipif/folded_context.json`
2. `data/security_results/knowledge/solodit_patterns.jsonl`
3. `data/security_results/loop/refinement_hints.json`
4. `data/security_results/knowledge/failure_signatures.jsonl`
5. `data/security_results/knowledge/concrete_candidates.jsonl`

If `folded_context.json` is missing, incomplete, or not `gate_ok` equivalent, write a short skipped note and do not create proposals.

## Workflow

1. Confirm the deterministic chain completed today and did not create `submission_alert.json`.
2. Select 5-12 high-quality Solodit patterns that match active targets or current refinement hints.
3. Convert only concrete analogues into proposal parameters that match NSS template parameter spaces.
4. Mark every proposal as untrusted and include Solodit lineage:

```json
{
  "template": "flash_loan_oracle",
  "parameters": {},
  "lineage": ["solodit:<id-or-slug>"],
  "delegate_note": "Solodit analogue: <title>; tags=<tags>; still requires NSS validation"
}
```

5. Write `data/security_results/hermes_proposals/solodit-YYYYMMDD.json`.
6. Update `data/security_results/hermes_proposals/latest.json` to the same payload.

## Proposal Contract

```json
{
  "run_id": "solodit-YYYYMMDD",
  "campaign_id": "solodit-hybrid-YYYY-MM",
  "target_slug": "<target>",
  "required_config": "src/night_shift_security/config/<target-config>.json",
  "allowed_templates": ["flash_loan_oracle"],
  "source_artifacts": [
    "data/security_results/knowledge/solodit_patterns.jsonl"
  ],
  "force_target": true,
  "metadata": {
    "trusted": false,
    "source": "solodit-research"
  },
  "proposals": []
}
```

Prefer one target per proposal file. If multiple targets look useful, choose the target with the strongest current refinement hint.

## Gotchas

- Solodit data is historical and may be catalogue-like. It can guide questions, not prove a live issue.
- Proposal parameter keys must match NSS `parameter_spaces.py`; invalid keys are dropped by `validate_hypothesis()`.
- Never include `CYFRIN_API_KEY` or raw private API output in proposal notes.
- Do not bypass `bounty loop --target`; target/config mismatches should fail fast.
