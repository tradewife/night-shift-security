---
name: shoestring-pack
description: Use when exporting zero-RPC shoestring Immunefi submission pack from pipeline findings JSON.
---

# Shoestring Pack Export

```bash
cd /home/kt/projects/rtp/night-shift-security

RUN_JSON=data/security_results/<date>/findings.json
.venv/bin/python -m night_shift_security.cli.main submission --input "$RUN_JSON"
```

Outputs under `data/security_results/bounty/shoestring/<exploit-id>/`:
- `README.md`, `NSS-*.md`, `NSS-*_repro.sh`, `manifest.json`

## Verify repro (free)

```bash
./data/security_results/bounty/shoestring/<exploit-id>/NSS-*_repro.sh
```

## Gotchas

- Defaults to min evidence grade 4. Lower with `--min-evidence-grade 3` only when justified.
- Crema / Kamino packs use fixture replay — no RPC in repro script.