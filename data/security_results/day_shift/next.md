# Session plan — next
Status: queued

## Objective

v6.8 flash-loan engine plumbing + Path B (`ixs_sysvar` in `MarginfiFuzzContext`).

## Blocks

- [ ] Path B — Plumb `ixs_sysvar` into `MarginfiFuzzContext::setup` so the `lending_account_start_flashloan`/`end_flashloan` flow exercises `validate_ixes_exclusive` under arbitrary-driven action sequences
- [ ] Extend `Action` enum (extend `lend_extended.rs`) with `StartFlashloan{idx, end_idx}` + `EndFlashloan{idx}` variants
- [ ] Re-run v6.7 orchestrator + long-fuzz; capture 7 attempts × 20 seeds + 90s+90s instrumented-release
- [ ] Try a parallel substrate — build Kamino/Drift fuzz crate (Marginfi is the template)

## Night Shift handoff

- Do **not** run the **full bounty-depth chain** unless engine substrate counts/iterations change materially
- Weekly: `platform sync --all`
- Intel: `data/security_results/intel/latest.md`