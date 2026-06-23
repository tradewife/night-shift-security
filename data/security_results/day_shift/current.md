# Session plan - v6.14 Origin close

Status: **closed** (2026-06-23) - v6.14/session-18 completed.

## Latest verified v6.14 run

v6.14 followed the user-directed Origin Protocol pivot after the v6.13 OnRe
submission-gated finding. The session prioritized ARM economic invariants first,
then Morpho V2 cross-chain Master/Remote accounting, while preserving the
submission gate discipline.

| Phase | Result |
|-------|--------|
| Origin source baseline | Pinned `arm-oeth` at `7e0c4868f341744f03ac45445254a1ace6e56338` and `origin-dollar` at `d78437879c5e96a5af2243ca1fd3cc92209192b4`; recorded `sources/origin/source_manifest.json`. |
| ARM JIT-1 | Local Foundry PoC measured a JIT LP capturing pending base-asset redemption discount release; fuzz property bounded profit by `pendingAssets * (1 - crossPrice)`. |
| Live ARM quantification | Ethena ARM at block `25381386`: `paused=true`, `pendingRedeemAssets=0`, `crossPrice=0.99996e36`; current extractable value `0`. |
| Morpho V2 cross-chain | Mainnet Master and Base Remote both nonce `24`, no pending transfer; Master undercounted Remote by `9.965163 USDC`, not an over-credit. |
| JIT monitor | Added `hermes/scripts/nss_origin_jit_monitor.py`; latest output says `needs_requantification=false`. |
| Gate | Origin `submit_ready=0`; `ORIGIN-ARM-JIT-1` remains research-grade only. |

## Blocks

- [x] OnRe v6.13 submittable pack preserved for human gate.
- [x] Origin ARM JIT-1 local PoC and research pack written.
- [x] Origin live ARM materiality check completed.
- [x] Morpho V2 cross-chain Master/Remote live snapshot completed.
- [x] Lightweight Origin JIT monitor added.
- [ ] Human-review and decide whether to submit `NSS-ONRE-1`.
- [ ] Continue Origin only if JIT monitor triggers or new Morpho/CrossChain state becomes material.
- [ ] First non-OnRe Origin candidate gated through `qualifies_for_submission()`.

## Night Shift handoff

- **Do not promote `ORIGIN-ARM-JIT-1`** unless live state shows unpaused ARM, non-zero `pendingRedeemAssets`, and material `pendingAssets * (1 - crossPrice)` after attacker dilution.
- Use `hermes/scripts/nss_origin_jit_monitor.py` for quick read-only JIT checks.
- Morpho V2 CrossChain currently looks conservative: Master cached balance is below Remote actual balance.
- OnRe `NSS-ONRE-1` remains the only current `submit_ready=1` human-gated pack.
- Preserve route discipline: `bounty/research/` for Origin; `bounty/submittable/` only after `qualifies_for_submission()`.

## References

- `SPEC.md` v6.14.0-origin-session18
- `CHANGELOG.md` v6.14.0-origin-session18
- `data/security_results/lab_notebook/2026-06-23-origin-deep-forensic.md`
- `data/security_results/investigations/2026-06-23-origin-deep-forensic/`
- `data/security_results/bounty/research/origin/ORIGIN-ARM-JIT-1.json`
- `hermes/scripts/nss_origin_jit_monitor.py`
