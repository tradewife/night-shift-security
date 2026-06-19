# Coding-Agent Orchestrator Loop — Night Shift Security

**Paste into Codex / Cursor / Claude Code.** This is the **outer engineering loop** for human-or-coding-agent sessions. It is **not** a Hermes cron job, Hermes skill, or scheduled Hermes prompt.

> Codex/Cursor is the foreman. Hermes is the night-shift machine. NSS Python gates are the judge.

## Two orchestration layers only

| Layer | What runs | Role |
|-------|-----------|------|
| **Layer 1** | `nss-hipif-chain`, optional Solodit proposal lane, NSS CLI, benchmarks | Existing Hermes/NSS machinery — deterministic evidence + gates |
| **Layer 2** | Coding-agent session (this doc) | Observe → diagnose → one substrate fix → test → commit → repeat |

**Hard rule:** Do not add new Hermes cron jobs unless Kate explicitly requests one.

## Mission

Drive `tradewife/night-shift-security` until NSS emits `data/security_results/loop/submission_alert.json` with `status=submit_ready` and a human can review a real Immunefi/Cantina package.

End state requires: live target, native harness, concrete candidate binding (commit + discriminator + accounts), candidate-specific PoC, measured non-fee impact, evidence grade ≥4, `qualifies_for_submission() == true`.

## Trust boundary

Never loosen: `validate_hypothesis()`, evidence grading, CPCV, credible harness gates, `submission_gates.py`, `qualifies_for_submission()`, `submission_alert.json`.

LLM/Solodit/AuditVault/benchmark outputs are advisory (`metadata.trusted=false`). No external submission. No mainnet exploitation.

## Session start

```bash
git pull --ff-only && pwd && git status --short
```

Read: `AGENTS.md`, `AUDIT.md`, `SPEC_V5_COMPLETION.md`, `data/security_results/lab_notebook/` (newest), `folded_context.json`, `native_harness_status.json`, `concrete_candidates.jsonl`, `~/.hermes/profiles/nightsoul/cron/output/` (latest HIPIF run).

## Loop

1. **Observe** — `hipif status`, `hipif gate`, `native status`; inspect cron output + impact artifacts.
2. **Diagnose** — one label: `B0`…`B9` (see bootstrap spec). `B8` = gates correct, not success.
3. **Pick one improvement** — smallest high-leverage substrate change.
4. **Implement** — code/tests only; no gate edits.
5. **Benchmark** — `pytest tests/test_benchmarks.py`
6. **Validate** — focused pytest, then broader suite.
7. **Run NSS** — existing scripts only when green: `nss-hipif-chain-run.py --phase deterministic` (not a new cron).
8. **Lab notebook** — `data/security_results/lab_notebook/YYYY-MM-DD-coding-agent-<slug>.md`
9. **Commit** — `nss(v5 …): …` after tests pass.

## Bottleneck labels

`B0_ENVIRONMENT` | `B1_CRON_ORCHESTRATION` | `B2_NO_NATIVE_HARNESS` | `B3_NO_CONCRETE_BIND` | `B4_NO_MEASURED_DELTA` | `B5_NO_CANDIDATE_POC` | `B6_FALSE_POSITIVE` | `B7_FALSE_NEGATIVE` | `B8_GATE_REJECTION_OK` | `B9_SUBMIT_READY`

## Anti-patterns

Relaxing gates; catalogue as novel; fee-only CPI as impact; Solodit as evidence; more trials instead of bindings; new Hermes cron for the coding agent.

## Output per loop

```
State: target, bottleneck, files, tests, benchmark, submit_ready, gate reason
Decision: continue | human gate | blocked
Next: one exact command or task
```