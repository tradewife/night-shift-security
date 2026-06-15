Hybrid HIPIF night chain. Bootstrap script already ran hipif init and **deterministic bulk depth** (scan, wormhole 12×, KLend live, cantina, hunt, RSI). Read `hipif status` output in context — `chain_status` should be `awaiting_agent`.

## Your phase (mandatory — do not stop early)
Complete **every remaining subgoal** from `current_subgoal` through `gate`:

1. **depth_wormhole_bridge** — operator-triage on `sources/wormhole/repo`; `nss-write-wormhole-triage-proposals.py`; bounty loop with `wormhole_shoestring.json` + proposals (`NSS_HIPIF_WORMHOLE_BRIDGE_TRIALS` default 4)
2. **refine_conditional** — read `refinement_hints.json`; **hypothesis-expansion** + `delegate_task` (parallel max 3); bounty loop with `--proposals`
3. **coordinator_conditional** — if Kamino hints: `coordinator plan` + `coordinator cycle` with `kamino_shoestring.json`
4. **journal_fold** — lab-notebook skill: same-vs-different vs prior run; append MEMORY.md
5. **gate** — operator-submit if `submission_alert.json` present; hard stop on `submit_ready`

## Rules (non-negotiable)
- Use hipif CLI hooks every turn: parse, ground, record, fold. Emit reflection/completion/subgoal/action tags.
- **Do NOT end your turn** until you run: `.venv/bin/python -m night_shift_security.cli.main hipif gate` and it exits **0**.
- If `hipif gate` exits 1, continue executing subgoals — cron success requires gate pass.
- No short text-only responses before gate passes.
- Never bypass NSS validation gates. Never post externally without Kate approval.