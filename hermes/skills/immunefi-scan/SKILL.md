---
name: immunefi-scan
description: Use when scanning curated Immunefi Solana programs with NSS zero-RPC engine. Reads latest scan report.
---

# Immunefi Scan

Zero-RPC catalogue probe — no LLM expansion inside scan.

```bash
cd /home/kt/projects/rtp/night-shift-security

# List curated programs
.venv/bin/python -m night_shift_security.cli.main scan --list --ecosystem solana

# Full scan
.venv/bin/python -m night_shift_security.cli.main scan --ecosystem solana --min-bounty 250000
```

Outputs (Solana-only legacy path):
- `data/security_results/immunefi_scan/latest.json`
- `data/security_results/immunefi_scan/latest.md`

Unified Immunefi + Cantina scan (used by `bounty-loop` / HIPIF `scan_all`):
```bash
.venv/bin/python -m night_shift_security.cli.main scan --platform all --min-bounty 250000
```
→ `data/security_results/bounty_scan/latest.json`

## Platform intel (live listings)

```bash
.venv/bin/python -m night_shift_security.cli.main platform sync --all
.venv/bin/python -m night_shift_security.cli.main platform diff
```
→ `data/security_results/platform/{immunefi_programs,cantina_programs,scope_registry}.json` (live platform coverage; sync before relying on counts)

## Triage

Flag programs with `scan_grade3_plus` and high max bounty. Compare week-over-week deltas for Kamino, Raydium, Orca, Marinade. `submittable_candidate` requires `qualifies_for_submission()` — distinct from grade-3+ scan signal.

**Next step:** autonomous hunt uses `bounty-loop` inside HIPIF chain. Manual deep-dive: `investigate-from-scan` for Immunefi-only `investigate` CLI.

## Gotchas

- Scan forces `llm_expansion.enabled: false` internally — do not pass `--proposals`.
- Curated registry (~30 programs) is a subset; `platform sync` is authoritative for live Immunefi/Cantina coverage gaps.
