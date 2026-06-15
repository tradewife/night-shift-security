---
name: operator-submit
description: Pre-submit checklist before external Immunefi/Cantina post — scope, PoC, KYC, deposit, duplicates.
---

# Operator Submit — External Bounty Gate

Use when `submission_alert.json` schema v2 shows `kate_action: approve_external_post` or a finding has `export_track: submittable`.

## Hard stops (never auto-post)

- `qualifies_for_submission()` must be true
- `export_track` must be `submittable` (not `research_surface`)
- v4 candidate binding must include schema >=4, source commit, target pin, selector/discriminator, reproduction artifact, measured impact
- Kate explicit approval in `submission_alert.json`
- PoC script runs green with balance delta or IMPACT evidence

## Checklist

1. **Scope** — `platform diff` + `data/security_results/platform/scope_registry.json`; confirm in-scope asset + impact class
2. **PoC** — run `bounty/submittable/<slug>/*_repro.sh` or `forge test --match-test <fork_test>`
3. **IVSS** — submittable markdown includes Brief, Details, Impact, IVSS, References
4. **KYC** — if `kyc_required: true`, prepare identity docs before dashboard submit
5. **Deposit** — if `deposit_usd > 0`, confirm budget (Cantina submission fee)
6. **Duplicates** — grep Immunefi/Cantina disclosed issues; catalogue analogues are not submittable
7. **v4 candidate** — inspect candidate payload, generated PoC result, failure trace status, and impact oracle measurement

## Commands

```bash
.venv/bin/python -m night_shift_security.cli.main platform sync --all
.venv/bin/python -m night_shift_security.cli.main platform diff
cat data/security_results/loop/submission_alert.json
ls data/security_results/bounty/submittable/
```

## Output

Update lab notebook with scope_check pass/fail, PoC command + exit code, and Kate decision.
