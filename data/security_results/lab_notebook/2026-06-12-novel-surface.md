# Lab entry — 2026-06-12

## Trigger
Day Shift continuation: novel-finding hunt after Kate gate (no catalogue Immunefi submits). Wormhole + Kamino KLend-native probes.

## Scan queue (prior)
- Wormhole: grade 1, $5M max, analogue `nomad-bridge-2022`
- Kamino/Mango, Raydium/Orca, Marinade: saturated — excluded from cron investigate

## Investigated

### Wormhole (`immunefi-wormhole-2026-06`)
- Config: `src/night_shift_security/config/wormhole_shoestring.json`, `targets/wormhole.json`
- Templates: `access_control_escalation`, `composability_risk`
- Proposals: `hermes_proposals/wormhole-cross-20260612-060508.json` (4 variants; fixed `access_control_escalation` param names)
- Coordinator: init + 4 cycles → **0 pending missions**
- Store stats: 132 records, 4 runs, `deployed_viable_count: 0`

### Kamino KLend native (`kamino-klend-2026-06`)
- Config: `src/night_shift_security/config/kamino_klend.json`, `targets/kamino-klend.json`
- **`exploit_id: ""`** — no Mango catalogue anchor; `always_test_catalog_solana_anchors: false`
- Pipeline run: 33 findings, 7/19 catalogue rediscovery (vs full-grid 19/19 on default)
- Coordinator: init + 3 cycles (flash_loan_oracle, composability_risk, reentrancy) → **0 pending**
- Store stats: 215 records, 4 runs, `deployed_viable_count: 0`, `catalog_analogue_count: 0`

## Engine outcome

| Target | Findings | deployed_viable | solana_reproduced | Best path |
|--------|----------|-----------------|-------------------|-----------|
| Wormhole | ~13 investigate + coordinator | 0 | 0 | simulation / grade 1 |
| Kamino KLend | 33 | 0 | 0 | flash_loan_oracle simulation |

No Immunefi packs emitted (`min_evidence_grade: 4` gate). No novel PoC.

## Same vs different
**Different** from Mango-anchored Kamino: empty `exploit_id`, disabled forced catalogue Solana anchors, KLend program IDs in target metadata. Rediscovery rate dropped (7 vs 19) but top vectors still oracle-flash patterns mapping to `mango-markets-2022` / `bzx-2020`.

**Same** limitation: mock simulator + no strict KLend validator replay → no `deployed_viable`, no submission-ready novelty.

## Code
- `nss-write-scan-proposals.py`: `access_control_escalation` uses `privilege_escalation_pressure`, `role_bypass_severity`, `zero_root_exploitability`, `target_role_preference`
- New configs: `kamino_klend.json`, `kamino-klend.json`, `wormhole_shoestring.json`, `wormhole.json`

## Night Shift handoff
- Cron OK: bounty scan refresh; investigate queue excluding saturated slugs (kamino, raydium, orca, marinade, wormhole)
- Cron skip: catalogue validator re-exports; Wormhole/Kamino coordinator (Day Shift completed cycles)
- Open for manual: archive `ETHEREUM_RPC_URL` for Wormhole EVM fork; KLend-specific validator harness (non-catalogue replay)

## Next action
Program-specific KLend oracle/borrow invariant tests or paid archive fork for Wormhole EVM — only paths likely to escape catalogue analogue.