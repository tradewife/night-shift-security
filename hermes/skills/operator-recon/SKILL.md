---
name: operator-recon
description: Discovery alpha — file triage, git patch mining, recon invariant tests before deep analysis.
---

# Operator Recon

Phase B discovery workflow. Run before `hypothesis-expansion` on a cloned target repo.

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
.venv/bin/python -m night_shift_security.cli.main triage wormhole-map \
  --repo /path/to/wormhole-clone \
  --output data/security_results/triage/wormhole_program_map.json
```

Canonical IDs land in `sources/wormhole/recon.json`. Catalogue analogue remains validation-only.

## Step 5 — Checkpoint + expansion

Write `operator-checkpoint` with `ranked_files` from triage output, then scoped `hypothesis-expansion` on files ≥4 only.

## Gotchas

- Triage requires a real git repo for `patches` (not bare `sources/` JSON)
- Kamino KLend validator harness: `NSS_KLEND_FIXTURE=1` in CI; live validator needs RPC + human gate per SOUL
- Invariant failures on `sources/kamino/recon.json` are expected — they feed refinement, not submission