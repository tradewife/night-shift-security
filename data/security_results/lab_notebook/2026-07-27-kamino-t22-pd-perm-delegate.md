# Lab notebook — 2026-07-27 Kamino T22 PermanentDelegate (KLEND-T22-001)

## Trigger
4d-chess-sequential deep dive on unexplored Kamino surfaces. Focus on Token-2022 extension inconsistency and the hardest cross-layer paths.

## Same vs different
**Same:** Primary Target Subsystem = KLend↔KVault↔Scope. Codegraph-x-ray artifacts reused.
**Different:** Moved from abstract invariant analysis to concrete mainnet-verified T22 PermanentDelegate drain with live inventory evidence.

## Finding: KLEND-T22-001
`check_only_supported_extensions_on_liquidity_mint()` in `constraints.rs` lists `ExtensionType::PermanentDelegate` in `SUPPORTED_LIQUIDITY_MINT_TOKEN_EXTENSIONS` but the `match` arm falls through to `_ => {}` — no validation. KLend explicitly validates TransferHook (program_id must be null), TransferFee (0 bps), ConfidentialTransfer (auto_approve false), DefaultAccountState (Initialized/Frozen), and Pausable (not paused) — but does NOT validate PermanentDelegate (no check at all).

**Live mainnet evidence (2026-07-27):**
- 21/30 T22 liquidity mints (70%) have non-null PermanentDelegate
- 66 reserves drainable via 7 unique PD holders
- Largest PD holder controls 11 mints across 66+ reserves
- Example: PYUSD-class mint with 26 reserves, PD holder `2apBGMsS6ti9RyF5TwQTDswXBWskiJP2LD4cUEDqYJjk`

**Attack chain:** PD holder → TransferChecked from KLend reserve_vault_ata → tokens permanently drained → KLend accounting unchanged → depositors lose funds irreversibly.

**Why submit_ready:** Immunefi OOS says "T22 issues without irrecoverable loss" but PermanentDelegate drain IS irrecoverable. KLend's inconsistent extension pattern (hardened against 5 classes but not the 6th that grants permanent token authority) is a code defect, not a design choice.

## Other findings (honest-zero / deferred)
- Elevation group over-borrow: honest-zero
- Ticket soft reservation: honest-zero
- Farms CPI: honest-zero
- SCOPE-ORD-001: confirmed but not triggerable (max live exp=18, threshold=19)

## submit_ready
**KLEND-T22-001 → provisional (needs human adjudication framing)**
- Evidence grade: 5 (code-confirmed + mainnet inventory)
- Reproducible: static analysis + RPC data; can deploy T22+PD mint to test if bounty allows
- Impact: irrecoverable fund loss (Critical)
- OOS framing challengeable: OOS says "no irrecoverable loss" but this HAS irrecoverable loss
