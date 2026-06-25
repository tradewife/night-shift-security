---
name: operator-recon
description: Discovery alpha — file triage, git patch mining, recon invariant tests before deep analysis.
---

# Operator Recon

Phase B discovery workflow. Run before `hypothesis-expansion` on a cloned target repo.

## Step 0 — v4 semantic map (preferred first pass)

```bash
cd /home/kt/projects/rtp/night-shift-security
.venv/bin/python -m night_shift_security.cli.main semantic map \
  --slug <slug> \
  --repo /path/to/repo
```

For Wormhole:

```bash
.venv/bin/python -m night_shift_security.cli.main semantic map \
  --slug wormhole \
  --repo sources/wormhole/repo \
  --kind bridge
```

Artifacts land under `data/security_results/semantic/<slug>/`; concrete candidates are upserted into `data/security_results/knowledge/concrete_candidates.jsonl`.

## Step 1 — File triage (score ≥4 only)

```bash
cd /home/kt/projects/rtp/night-shift-security
.venv/bin/python -m night_shift_security.cli.main triage files \
  --repo /path/to/klend-repo \
  --slug kamino \
  --min-score 4 \
  --output data/security_results/triage/kamino_files.json
```

## Step 2 — Git patch shapes

```bash
.venv/bin/python -m night_shift_security.cli.main triage patches \
  --repo /path/to/klend-repo \
  --slug kamino \
  --output data/security_results/triage/kamino_patch_shapes.jsonl
```

Pass ranked paths for analogue hints:

```bash
  --ranked-file programs/klend/src/oracle.rs \
  --ranked-file programs/klend/src/borrow.rs
```

## Step 3 — Recon invariant tests

```bash
.venv/bin/python -m night_shift_security.cli.main invariants test \
  --from-recon sources/kamino/recon.json \
  --output-dir data/security_results/invariants
```

Failures → `refinement_seeds` for RSI / `hypothesis-expansion` context.

## Step 4 — Wormhole program map (Block B)

For Wormhole targets (not Nomad proxy analogue):

```bash
# One-time clone (sparse solana + ethereum):
git clone --depth 1 --filter=blob:none --sparse https://github.com/wormhole-foundation/wormhole.git sources/wormhole/repo
cd sources/wormhole/repo && git sparse-checkout set solana ethereum

.venv/bin/python -m night_shift_security.cli.main triage files \
  --repo sources/wormhole/repo --slug wormhole --min-score 4 \
  --output data/security_results/triage/wormhole_files.json

.venv/bin/python -m night_shift_security.cli.main triage wormhole-map \
  --repo sources/wormhole/repo \
  --output data/security_results/triage/wormhole_program_map.json
```

Canonical IDs land in `sources/wormhole/recon.json`. Catalogue analogue remains validation-only.

Scoped proposals (no delegate required for parametric pass):

```bash
.venv/bin/python hermes/scripts/nss-write-wormhole-triage-proposals.py --min-score 5
.venv/bin/python -m night_shift_security.cli.main --config src/night_shift_security/config/wormhole_shoestring.json \
  --proposals data/security_results/hermes_proposals/latest.json run
```

## Step 5 — Static tool ingestion (optional)

```bash
.venv/bin/python -m night_shift_security.cli.main tools opengrep \
  --slug <slug> --repo /path/to/repo
```

If `opengrep`/`semgrep` is absent, `tool_missing` is non-fatal. SARIF findings never bypass validation.

## Step 6 — Checkpoint + expansion

Write `operator-checkpoint` with `ranked_files` from triage output, then scoped `hypothesis-expansion` on files ≥4 only.

## Gotchas

- Triage requires a real git repo for `patches` (not bare `sources/` JSON)
- Kamino KLend validator harness: `NSS_KLEND_FIXTURE=1` in CI; live validator needs RPC + human gate per SOUL
- Invariant failures on `sources/kamino/recon.json` are expected — they feed refinement, not submission
- Generated candidates from tests or generated directories are lower value; prefer production source paths in semantic artifacts.
