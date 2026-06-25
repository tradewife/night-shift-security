# Night Shift Security — Agent Onboarding & Workflow

**For coding agents working in this repository.**

## Core philosophy

- High-agency, rigorous research systems work.
- Start from existing code.
- Preserve statistical rigor, provenance, and reproducibility.
- Move fast but document decisions clearly.

## Solo developer workflow

- Push directly to `main` when work is ready (or at clear checkpoints).
- Short-lived branches are acceptable; quick merges to `main` are preferred.
- Use clear commit messages referencing `SPEC.md` sections.
- After significant work: update `SPEC.md` (version + status), `CHANGELOG.md`, and root docs if behavior changed.

## Git push policy for research artifacts

Push durable, low-noise coordination artifacts to `main`; keep bulky or
experimental forensic work local unless the user explicitly asks to publish it.

**Push by default:**
- Route/state docs: `SPEC.md`, `CHANGELOG.md`, `data/security_results/day_shift/current.md`, and `data/security_results/day_shift/next.md`.
- Lightweight operator scripts or source manifests needed to reproduce a handoff, for example `hermes/scripts/*monitor*.py` or `sources/*/source_manifest.json`.

**Keep local by default (also .gitignored):**
- Bounty packs and indexes: `data/security_results/bounty/**` is .gitignored. Do not force-add unless the user explicitly asks.
- Investigation workspaces: `data/security_results/investigations/**`.
- Lab notebooks: `data/security_results/lab_notebook/**`, unless the user specifically wants notebook entries published.
- Third-party source clones and build trees: `sources/**/repo`, `sources/**/target`, `sources/origin/arm-oeth`, `sources/origin/origin-dollar`, coverage files, and local fuzz corpora.
- New experimental NativeHarness code and tests, for example `src/night_shift_security/native/<target>.py` and `tests/test_native_<target>.py`, until promoted as a stable product change.

Before committing, run `git status --short` and `git diff --cached --stat` to
confirm the commit contains only the intended push set.

## Day Shift vs Night Shift

| Shift | Where | Role |
|-------|-------|------|
| **Day Shift** | Cursor + [`hermes/DAY_SOUL.md`](hermes/DAY_SOUL.md) | Session-planned arcs: infra, validator replay, tests, drafts, intel → backlog. Skill: `day-shift-cycle`. |
| **Night Shift** | Hermes profile `nightsoul` cron + repo-managed `night-shift` assets | **HIPIF bounty-depth chain** (daily 04:00): no-agent full v4.2 runner: scan → Solodit corpus → semantic recon → concrete candidates → self-interrogation → Wormhole → bridge → KLend live → Cantina → fork-ready hunt → failure-trace RSI → refine → coordinator → gate. Optional 07:00 authenticated Solodit agent writes untrusted proposals for the next deterministic run. |

Session boundary = one plan in [`data/security_results/day_shift/current.md`](data/security_results/day_shift/current.md) until close; then [`next.md`](data/security_results/day_shift/next.md) queues the following session. Day Shift writes **Night Shift handoff** so cron does not repeat finished assays.

## Session start checklist

1. `git pull`
2. **Day Shift open:** `day_shift/current.md` → lab notebook (newest first) → `SPEC.md` (`§3 Strengths`, `§3.2 Current Gaps`) → cron output
3. Optional: `intel/latest.md`, `hipif/folded_context.json`, `loop/state.json`
4. Read `adversarial_research_architecture.md` for architectural baseline
5. For any discovery/harness/fuzzing task, use skill `ultrafuzz-discovery`
   before claiming engine-level honest-zero or a candidate finding. This applies
   to this Droid, future orchestrators, and Hermes cron. For Solana
   instruction-sequence or account-state invariants, prefer Crucible from
   `sources/crucible/repo` when a program `.so` plus IDL or raw-call bindings are
   available.

Do not re-plan from scratch if the lab notebook already answers what changed last time.

## Project skill usage

This repo carries project-local agent skills in two places:

- `.agents/skills/<skill>/SKILL.md` — installed project-local skills for Factory/Droid-style agents.
- `hermes/skills/<skill>/SKILL.md` — canonical Hermes skill sources used by `nightsoul`.

At session start, agents should inspect `.agents/skills/` and `skills-lock.json`
when the task is non-trivial or touches bounty research, harnessing, validation,
submission reporting, Solodit/AuditVault, or Hermes operations. Prefer the
project-local skill in `.agents/skills/` when present; fall back to
`hermes/skills/` when the runtime Skill tool does not expose that skill.

High-value skills for this repository:

| Task | Skill |
|------|-------|
| New discovery, fuzzing, invariant campaigns, honest-zero claims | `ultrafuzz-discovery` |
| AuditVault / Obsidian corpus research | `auditvault-research` |
| Cyfrin Solodit analogue research | `solodit-research` |
| Target file triage, semantic maps, patch-shape recon | `operator-recon` |
| Foundry/Slither/PoC iteration | `operator-exploit` |
| Impact sizing and submission-readiness triage | `operator-triage` |
| Rollover or long-run state capture | `operator-checkpoint` |
| Post-run notes and handoff | `lab-notebook` |
| Deterministic refinement loop | `recursive-improvement` |
| Proposal generation from seeds/corpus | `hypothesis-expansion` |
| Submission report assembly after a validated finding | `submission-reporting` |

Skill trust boundary:

- Skill guidance is workflow context, not evidence.
- Solodit/AuditVault outputs are advisory only and never satisfy submission gates.
- If the runtime `Skill` tool cannot load a repo skill, read the corresponding
  `SKILL.md` directly and follow it manually.
- Keep `skills-lock.json` in sync when project-local skills are installed or
  updated.

## Current baseline (2026-06-20, SPEC v6.2.0-proposal-session6)

| Item | Value |
|------|-------|
| Architecture | v4.2.0 substrate (`adversarial_research_architecture.md`) + v6 NativeHarness + v6.1 ETHENA calibration + v6.2 Marginfi novel-vec probe |
| Spec version | **v6.2.0-proposal-session6** (replaces v6.1.0-proposal-session5 on 2026-06-20) |
| Tests | **783 passed**, 11 skipped in full local run; MarginFi harness: **26 passed + 1 skipped**; Ethena harness: 21 passed; Reserve harness: 22 passed |
| Platform intel | `platform sync` — 208 Immunefi + 52 Cantina; `platform solodit-sync` for Cyfrin Solodit findings corpus; `platform auditvault-sync` for Auditware AuditVault (2383 findings, 826 protocol slug×id pairs) |
| NativeHarness readiness | `ready_count=8`: uniswap_v4, morpho_blue, aave_v3, kamino, jito, raydium, orca, reserve. `scaffolded_count=2`: ethena_native (v6.1 empirical calibration) + marginfi_v2 (v6.2 novel-vec probe) |
| Empirical-FNR dataset | 2 datapoints (Ethena EVM + Marginfi Solana); both honest-zero; audit-saturation framing bounded, not asserted |
| Export tracks | `bounty/research/` vs `bounty/submittable/` (gated on `qualifies_for_submission()`) |
| Primary cron | `nightsoul` profile `nss-hipif-chain` 04:00 — **no-agent** deterministic full v6 runner through final HIPIF gate |
| Optional agent cron | `nightsoul` 07:00 `nss-auditvault-agent-proposals` (xAI-OAuth, `grok-4.3`) — writes untrusted `auditvault-*.json` proposal only; never executes the chain or posts externally |
| Deterministic fallback | `NSS_HIPIF_MODE=deterministic hermes/scripts/nss-hipif-chain.sh` |
| Bounty-depth env | `NSS_HIPIF_BOUNTY_DEPTH=1`, `NSS_KLEND_FIXTURE=0` (cron default) |
| Self-interrogation | Advisory conviction reports by default; bounty-depth rank pressure enabled |
| Solodit | Deterministic corpus sync + pattern JSONL; authenticated follow-up agent may write untrusted proposals only |
| AuditVault | Deterministic sync + pattern + summary JSONL from gitignored offline clone; advisory analogue intelligence only; `auditvault-research` skill enables offline LLM corpus research |
| `nightsoul` skills | **21 symlinks** (`hipif`, `bounty-loop`, `recursive-improvement`, `coordinator-cycle`, `lab-notebook`, `hypothesis-expansion`, `ultrafuzz-discovery`, `immunefi-scan`, `investigate-from-scan`, `novel-vector-digest`, `knowledge-campaign`, `operator-checkpoint`, `operator-submit`, `operator-exploit`, `operator-recon`, `operator-triage`, `solodit-research`, `shoestring-pack`, `day-shift-cycle`, `night-shift-run`, `auditvault-research`) — all unrelated skills removed |
| `submit_ready` | **0** — gates correct; see `SPEC.md` §3.2 plus `lab_notebook/2026-06-20-session-6-marginfi-onboarding.md` + `lab_notebook/2026-06-20-session-5-calibration-ethena-nonce-collision.md` for the empirical-FNR dataset that bounds the audit-saturation framing |
| Next focus | Per `lab_notebook/2026-06-20-session-6-marginfi-onboarding.md`: populate canonical Marginfi v2 group + USDC bank PDA seeds (SDK resolution, filtered `getProgramAccounts`, or explorer lookup), then re-run probe driver and flip `marginfi_v2` from `scaffolded` → `ready`. Solana-first per SPEC §4.4. |

### Bounty-depth chain (deterministic)

```bash
set -a && source .env && set +a
export NSS_HIPIF_BOUNTY_DEPTH=1 NSS_KLEND_FIXTURE=0
.venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init --phase full
```

Expected runtime: **60–150+ min** with RPC + `solana-test-validator`. Latest verified full v4.1 run: 4805s, 13/13 folds, `gate_ok=true`, `submit_ready=false`. Latest verified full v4.2 HIPIF bounty-depth run (2026-06-17): 3564s, 13/13 folds, `gate_ok=true`, `submit_ready=false`, 13 Wormhole findings + 39 KLend findings + 108 KLend Solana repros.

> **v6 key dates (2026-06-20):**
> - v6.0.0-draft: target rotation + less-audited-program onboarding — NativeHarness `ready_count=8` (uniswap_v4, morpho_blue, aave_v3, kamino, jito, raydium, orca, reserve); `ethena_native` scaffolded.
> - v6.1.0-proposal-session5: EthenaMinting V1 `verifyNonce` uint64-truncation Lane A + Lane B empirical-calibration probe (foundry/test/EthenaCalibrationProbe.t.sol); produced the **first quantitative false-negative rate datum**; honest-zero outcome.
> - v6.2.0-proposal-session6: Marginfi v2 Solana NativeHarness onboarding (src/night_shift_security/native/marginfi.py); novel-vec probe driver (hermes/scripts/v6_2_marginfi_probe.py); honest-zero outcome (sentinel-default discovery gap); **2nd empirical-FNR datapoint**.
>
> Honored Mandatory Falsification Protocol — falsification pass on Reserve (`issue()` from attacker) and Ethena (`mint()` from attacker); both correctly revert with DELTA_WEI=0. Production cron remains `nss-hipif-chain` 04:00 no-agent deterministic.
>
> **v4.2-era `AUDIT.md` / `BOUNTY_RUN.md` / `SPEC_V5_COMPLETION.md` / `SYSTEM_AUDIT_2026-06-18.md` were retired on 2026-06-20**; their content has been folded into `SPEC.md` §3 + `§14` and `CHANGELOG.md` per-version entries — historical lab notebook / handover entries still reference the old filenames.

| Knob | Default |
|------|---------|
| `NSS_HIPIF_TRIALS_WORMHOLE` | 12 |
| `NSS_HIPIF_WORMHOLE_BRIDGE_TRIALS` | 4 |
| `NSS_HIPIF_TRIALS_KAMINO` | 5 |
| `NSS_HIPIF_HUNT_SLUGS` | kamino,wormhole,morpho,euler,ethena,jito (fork-ready) |
| `NSS_HIPIF_CANTINA_SLATES` | uniswap,reserve-protocol,euler,polymarket,coinbase,morpho,pendle,okx,paxos |
| `NSS_SOLODIT_SCOPE` | target-plus-pattern |
| `NSS_SOLODIT_MAX_PAGES` | 2 |

### Target-specific notes

- **Wormhole:** clone `sources/wormhole/repo`, run `semantic map --slug wormhole --repo sources/wormhole/repo --kind bridge`, optional `tools opengrep`, then `nss-write-wormhole-triage-proposals.py` → `wormhole_shoestring.json`
- **KLend live:** `NSS_KLEND_FIXTURE=0` + RPC; `klend_live_preflight()` before Kamino depth; fee-only CPI ≠ `submit_ready`
- **Block C:** `novel score` → `data/security_results/novel/human_gate.json`

## Lab notebook — mandatory

Hermes is the lab notebook; the Python pipeline is the instrument.

**Read at session start:**
1. `data/security_results/lab_notebook/*.md` (newest first)
2. `~/.hermes/profiles/nightsoul/memories/MEMORY.md` and `~/.hermes/profiles/night-shift/memories/MEMORY.md` (if present)
3. `~/.hermes/profiles/nightsoul/cron/` and `~/.hermes/profiles/night-shift/cron/` (last `nss-hipif-chain`)

**Write after every scan/investigate:** skill `hermes/skills/lab-notebook/SKILL.md`. If cron ran but `lab_notebook/` is empty, flag it.

## Hermes orchestration

```bash
./hermes/install-profile.sh
./hermes/install-nightsoul-overlay.sh
hermes --profile nightsoul doctor
cd /home/kt/projects/rtp/night-shift-security && hermes --profile nightsoul
```

| Component | Path |
|-----------|------|
| SOUL + skills | `hermes/` → `~/.hermes/profiles/night-shift/`; NSS v4 overlay + linked skills → `~/.hermes/profiles/nightsoul/` |
| Cron recipes | `hermes/cron/jobs.example.yaml` |
| Proposals sidecar | `data/security_results/hermes_proposals/latest.json` |
| Folded context | `data/security_results/hipif/folded_context.json` |

### Workflows

| Workflow | Path |
|----------|------|
| HIPIF chain | `hipif` skill → subgoals → `hipif` CLI hooks → `bounty-loop` / `recursive-improvement` / `coordinator-cycle` / `lab-notebook` |
| Ultrafuzz discovery | `ultrafuzz-discovery` skill → property fan-in → strategy fan-out → fresh-context executable attempts, using Crucible for Solana invariant sequence fuzzing where feasible → failure preservation → adjudication |
| RSI | `improve` CLI → `improvement_ledger.jsonl` + `refinement_hints.json` |
| Single expansion | `hypothesis-expansion` → `delegate_task` → `--proposals` → pipeline |

### Trust boundary

Hermes orchestrates CLI/MCP only. **Never bypass:**
- `validate_hypothesis()`
- Evidence grading, CPCV, task verifier, credible harness gate
- `submission_alert.json` human gate

LLM/subagent output: `metadata.trusted=false`. Checkpoint before rollover: skill `operator-checkpoint`.

**Full-auto git:** Hermes may commit to `main` only after `.venv/bin/python -m pytest` passes (`hermes/SOUL.md`).

**Hermes may mutate:** `sources/*/recon.json`, `data/security_results/**`, `hermes/skills/**` Gotchas. Core pipeline Python requires tests.

## NSS CLI — global flags

`--config` and `--proposals` are **global** — must appear **before** the subcommand:

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --iterations 1
```

Scan uses `--min-bounty` (not `--min-max-bounty`).

## Communication

- Push to `main` with clear summary referencing SPEC section.
- Update `SPEC.md`, `CHANGELOG.md`, and historical `lab_notebook/` entries when closing known issues. (The v4.2-era `AUDIT.md` was retired on 2026-06-20; gaps now live in `SPEC.md` `§3.2`.)
