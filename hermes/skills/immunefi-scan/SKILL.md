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

Unified Immunefi + Cantina scan (used by `bounty-loop`):
```bash
.venv/bin/python -m night_shift_security.cli.main scan --platform all --min-bounty 250000
```
→ `data/security_results/bounty_scan/latest.json`

## Triage

Flag programs with catalogue analogues and high max bounty. Compare week-over-week deltas for Kamino, Raydium, Orca, Marinade.

**Next step:** autonomous hunt uses `bounty-loop` skill (unified `bounty_scan`). Manual deep-dive: `investigate-from-scan` for Immunefi-only `investigate` CLI.

## Gotchas

- Scan forces `llm_expansion.enabled: false` internally — do not pass `--proposals`.
- 12 programs in curated registry (not all 213 Immunefi Solana programs).