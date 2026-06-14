Execute the full HIPIF night chain per hipif skill. Bootstrap script already ran hipif init with bounty_depth=1.

## Subgoal order (do not skip or reorder)
bootstrap → scan_all → depth_wormhole → depth_wormhole_bridge → kamino_preflight → depth_kamino → cantina_slates → hunt_rotation → rsi_fold → refine_conditional → coordinator_conditional → journal_fold → gate

## Hermes intelligence requirements (mandatory)
1. Use hipif CLI hooks every turn: parse, ground, record, fold. Emit reflection/completion/subgoal/action tags.
2. Before depth_wormhole_bridge: operator-triage on sources/wormhole/repo if proposals stale; write triage proposals before loop.
3. refine_conditional: MUST use hypothesis-expansion + delegate_task (parallel max 3) from refinement_hints.json — not parametric-only reruns.
4. hunt_rotation: if scan shows uninvestigated high-bounty slug, delegate 1 expansion batch before loop tick.
5. coordinator_conditional: run coordinator-cycle when Kamino hints present.
6. journal_fold: lab-notebook with same-vs-different vs prior run; append MEMORY.md.
7. gate: operator-submit if submission_alert.json exists. Hard stop on submit_ready.

## Observability
After each depth subgoal, fold metrics: fork_reproduced, solana_reproduced, findings, harness markers (HARNESS_MODE, MEASURED_DELTA_LAMPORTS).
If a terminal command is blocked, log the block reason and try an alternate grounded command — do not mark subgoal complete on empty/error output.

Never bypass NSS validation gates. Never post externally without Kate approval.