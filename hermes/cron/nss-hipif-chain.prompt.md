Hybrid HIPIF night chain, SPEC v4.2.0. Bootstrap script already ran hipif init and **deterministic bulk depth** (scan, Solodit corpus, Wormhole semantic recon, self-interrogation, Wormhole 12×, KLend live, Cantina, hunt, RSI). Read `hipif status` in script output — **do not start until** `agent_phase_ready: true` (`bulk_phase_complete: true`, `chain_status: awaiting_agent`). If not ready, run `hipif status` and wait/poll; never fold bulk subgoals yourself.

## Your phase (mandatory — do not stop early)
Complete **every remaining subgoal** from `current_subgoal` through `gate`:

1. **depth_wormhole_bridge** — ensure `semantic map --slug wormhole --repo sources/wormhole/repo --kind bridge` is current; run `tools opengrep` if available; operator-triage; `nss-write-wormhole-triage-proposals.py`; bounty loop with `--target wormhole`, `wormhole_shoestring.json`, and proposals (`NSS_HIPIF_WORMHOLE_BRIDGE_TRIALS` default 4)
2. **refine_conditional** — read `refinement_hints.json` and `failure_signatures.jsonl`; run `traces summarize --slug <slug>` if traces exist; **hypothesis-expansion** + `delegate_task` (parallel max 3); target-pinned bounty loop with `--proposals` and `--target <slug>`
3. **coordinator_conditional** — if Kamino hints: `coordinator plan` + `coordinator cycle` with `kamino_shoestring.json`
4. **journal_fold** — lab-notebook skill: same-vs-different vs prior run; append MEMORY.md
5. **gate** — operator-submit if `submission_alert.json` present; hard stop on `submit_ready`

When any remaining subgoal involves harnesses, fuzzing, local mirrors,
validator replay, or an honest-zero/candidate claim, invoke
`ultrafuzz-discovery` first. The cron agent must write property fan-in,
strategy attempts, failure artifacts, and adjudication before folding. For
Solana instruction-sequence/account-state invariants, prefer Crucible from
`sources/crucible/repo` when a compiled program `.so` plus IDL or raw-call
bindings are available.

## Rules (non-negotiable)
- Use hipif CLI hooks every turn: parse, ground, record, fold. Emit reflection/completion/subgoal/action tags.
- **Do NOT end your turn** until you run: `.venv/bin/python -m night_shift_security.cli.main hipif gate` and it exits **0**.
- If `hipif gate` exits 1, continue executing subgoals — cron success requires gate pass.
- No short text-only responses before gate passes.
- Never bypass NSS validation gates. Never post externally without Kate approval.
- v4.2 submit-ready requires concrete candidate schema >=4, source commit, selector/discriminator, candidate-specific reproduction artifact, and measured non-fee impact. Self-interrogation conviction reports and Solodit analogues are advisory and do not satisfy submission gates. Triage-only Wormhole and fee-only KLend remain research-only.
- Fixed-input replay is not fuzzing. Do not claim engine-level honest-zero unless
  `ultrafuzz-discovery` artifacts show real executable attempts, observed actions,
  failure preservation, and adjudication.
- Crucible `--dry-run`, `--replay`, and coverage-only runs are not fuzzing; only
  real exploration runs count toward pass@k.
