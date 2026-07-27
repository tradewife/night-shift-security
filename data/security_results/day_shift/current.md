# Session plan — current

**Status: submit_ready=1 (KLEND-T22-001 provisional). Kamino cross-layer codegraph-x-ray complete; T22 PermanentDelegate finding advanced to submission gate.**

> **Cross-target open (2026-07-27 — v6.62.0, Kamino Finance deep-dive x-ray):**
> Operationalized user handoff for Kamino Immunefi ($1.5M Critical). Primary Target Subsystem = **KLend ↔ KVault ↔ Scope** under flash loans, vault AUM/share pricing, ticket progress CPI, and multi-source oracle chains.
>
> **Delivered:** cloned `sources/kamino/kvault@1d146d7` + `scope@0d7320b` (klend already `@23b9f2b`); codegraph indexes (klend 2821n/7159e, kvault 906/1661, scope 1281/2558); `invariants.md` + `property_candidates.md` (PROP-X-001..050) + 5 STRAT-X-* files; recon.json v2.0.
>
> **Key finding:** KLEND-T22-001 — Token-2022 PermanentDelegate allowlisted without validation. 21/30 T22 liquidity mints have live PD set; 66 reserves drainable by 7 unique PD holders. Code-confirmed + mainnet inventory confirmed. submit_ready provisional.
>
> **Prior Kamino reconciliation:** v6.8 flash fee H1/H3/H4 falsified (do not redo); v6.9 discriminator-blocked (prefer LiteSVM/local build); H2/H5 carried as PROP-X-040/041 secondary.
>
> Local artifacts: `data/security_results/investigations/2026-07-27-kamino-cross-layer/`.
> submit_ready=1 (KLEND-T22-001 provisional, needs human adjudication).

> **Prior closeout (2026-07-26 — v6.61.1, Rootstock PowPeg extended 4d-chess-sequential):**
> Single-thread 4d-chess-sequential session over `bc_advance`+`auth_tx`+`btctx`+`upgrade`+ Java `PowHSMSignerMessage`+`ECDSACompositeSigner`+ `BridgeSupport.addSignature`. All 9 strategies from v6.61.0 mapped onto canonical fix-points and verified fixed via Python oracle. **5.6.2 macro flip on `BLOCK_ALREADY_VALID()` confirmed**; test 107 returns expected `0x6b95 MERKLE_PROOF_MISMATCH`.
>
> **F-POW-001** — `btctx.c` unsigned-underflow on varint=0 script length. Reproduced in C-source simulator (`harness/nss_unsigned_underflow_probe.py`). Severity **MEDIUM** (HSM DoS). Not promoted to submit_ready.
>
> Engine-level honest-zero EXTENDED. submit_ready=0 unchanged.
> Local artifacts: `data/security_results/investigations/2026-07-25-rootstock-powpeg/harness/`, `data/security_results/lab_notebook/2026-07-26-rootstock-powpeg-4dchess-seq.md`.

## Completed this arc (Kamino)

| Step | Surface | Result |
|---|---|---|
| Clone | kvault + scope | done |
| codegraph init/index | 3 repos | done |
| x-ray invariants | Primary subsystem | done |
| property candidates | PROP-X-* | done |
| strategies | 5 STRAT-X-* ≥70% Primary | done |
| Executable pressure | flash↔vault / ticket / scope | done (honest-zero) |
| T22 PermanentDelegate | KLend constraints.rs | **submit_ready** |

## Night Shift handoff

- **KLEND-T22-001 is submit_ready (provisional)** — needs human adjudication on framing vs Immunefi OOS
- Prefer kamino proposals targeting **PROP-X-001..032** (cross-program)
- **Do not** re-run pure KLend flash fee purity (v6.8)
- Rootstock PowPeg remain parked pending docker `hsm:mware` / RSKIP surveys
- Horizen: Phase B re-eval still dated 2026-07-27 if schedule requires
