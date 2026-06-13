---
name: operator-checkpoint
description: Persist operator state before context rollover or session end during mid-investigation hunts.
---

# Operator Checkpoint

Write `data/security_results/operator/checkpoint.json` when context is nearly full or before ending a mid-investigation session.

## When to write

- Context rollover imminent
- Session end with open hypothesis
- Before `--trials` multi-attempt runs on a high-priority target

## Write

```bash
cd /home/kt/projects/rtp/night-shift-security
.venv/bin/python -m night_shift_security.cli.main operator checkpoint write \
  --target-slug kamino \
  --hypothesis "KLend oracle staleness borrow bypass" \
  --reason rollover \
  --next "bounty loop --trials 30 --refresh-scan"
```

## Read / clear

```bash
.venv/bin/python -m night_shift_security.cli.main operator checkpoint read
.venv/bin/python -m night_shift_security.cli.main operator checkpoint clear
```

## Resume protocol

1. Read checkpoint
2. Run `next_commands` in order
3. Append lab notebook entry noting resume vs fresh start

## Gotchas

- Checkpoint does not replace lab notebook — write both
- `next_commands` are hints; Hermes must still follow SOUL trust boundary (no gate bypass)