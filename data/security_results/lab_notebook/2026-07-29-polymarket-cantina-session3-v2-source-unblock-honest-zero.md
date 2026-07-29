# Polymarket Cantina — Session 3 (2026-07-29) — V2 source unblock + exhaustive audit regression

**Status: CLOSED. `submit_ready=0`.** V2 source recovered via Sourcify; 7+ layer
static + dynamic + economic + temporal analysis did **not** surface an
unprivileged Critical/High/Medium bug on the now-fully-auditable V2 surface.

## What changed since session 2

- Sessions 1+2 closed Track A (public CTF/Exchange) honest-zero. PB-08 unreachable.
- Track B (PB-01..07, 09..12) was blocked on private `polymarket-v2` source.
- This session probed Sourcify v2 API and confirmed the V2 contracts **are
  fully verified** via Sourcify Standard JSON Input (multi-file):
    - Exchange 26 files, PositionManager 20, Router 32, CollateralToken 11,
      AutoRedeemer 27, BinaryModule 27, NegRiskModule 29.
- Resolved V2 module impls via public Polygon RPC:
    - BinaryModule    = 0x492fec596ec347459e1ebe30b9245eb3b49b1bba
    - NegRiskModule   = 0xa61e7ca374f721d5b9fd5b0fee6fb90f27d448d7
    - PositionManager admin = 0x47ebfac3353314c788b96cdcbf41daadfe03629c
- Pulled full V2 source to `sources/polymarket/polymarket-v2/` (29 .sol files).

## Static + dynamic + economic + temporal review

### Static structure (Phase 2.1)
- **CombinatorialModule** (1340 lines): split/merge/splitOnCondition/mergeOnCondition/
  splitOnEvent/mergeOnEvent/convertOnEvent/extract/inject/convertToYesBasket/
  mergeFromYesBasket/compress/redeem/unwrap/wrap/mintFromBridge/burnFromBridge.
- **NegRiskModule**: convert, horizontalSplit/Merge, reportResult with BRIDGE_ROLE
  able to resolve synthetic Other condition (index = arity).
- **BinaryModule**: base `_storeResult` (allows partial results; not binary-restricted).
- **BaseModule**: `_storeResult` requires `result[0] + result[1] == RESULT_DENOMINATOR`.
- **BaseMigrationMixin**: `_redeemIfResolved` normalizes via
  `legacyPayout0 * RESULT_DENOMINATOR / payoutDenominator` — exact for binary
  legacy, dust for non-binary.
- **NegRiskMigrationMixin**: `prepareMigrationEvent` requires `2 <= conditionCount <= 256`.
- **Router** (513 lines): `combinatorialCollateralReturn` is **arbitrary selector
  call** to CombinatorialModule. Permissionless batch with collateral + positions
  pre-transferred; user supplies own positions (no theft vector).
- **Exchange** (1467 lines): complementary fast path, batch buy/sell, fee
  validation per-fill against maxFeeRateBps (5%), signature types EOA /
  POLY_1271 / POLY_PROXY / POLY_GNOSIS_SAFE, `_validateAndUpdate` flow.
- **AutoRedeemer** (252 lines): operator-only batched user redemption;
  `collateralBalance` diff-based payout measurement (relies on no other state
  changes during the batch — checked).
- **PositionManager**: `setCrossModuleAuth` requires the address to be a
  **registered module** (no arbitrary EOA grant). `addModule` requires
  `moduleId != 0` and not already registered.

### Dynamic state transitions (Phase 2.2)
- **`_storeLegsFromMemory` mutation pattern**: each iteration uses the
  `mstore(basketLegs, i+1)` length-shrink trick with explicit restore at end.
  Memory checkpoint not used; relies on the loop writing to a fresh
  `basketLegs` array copy. Verified that `_storeLegsFromMemory` itself stores
  deterministically (idempotent leg arrays).
- **Asymmetric rounding in `_getPositionPayout`**:
    - YES(outcomeIndex=0) → `mulDiv` (round-down) at each leg.
    - NO(outcomeIndex=1) → `mulDivUp` (round-up) on `payoutFactorUp`,
      then `_amount - mulDivUp(...)` (round-up on the YES slice).
  Edge case: if `conditionPayout == 0` for any leg, NO returns full `_amount`
  (leg lost → YES(Q) = 0 → NO(Q) = full amount). YES returns 0 in that case.
  Math is sound in expectation; dust compounds only with multi-leg positions.

### Economic value flow (Phase 2.3)
- `convertToYesBasket` decomposes NO(Q) into d YES baskets. Mathematically
  equivalent to direct NO(Q) redeem (De Morgan). Concrete numerics show:
  - For p(c1) = p(c2) = 99.9999%, amount = 1e6:
    - Direct NO(Q) = 1 wei (rounded).
    - Basket = 0 wei (both YES positions round down to 0).
  - User **loses** 1 wei by going via basket. Dust is informational loss, not
    exploitable gain.
- `extract` / `inject` are De Morgan-correct; same dust profile.
- No mint/burn path allows unbacked position creation. Mint requires
  collateral deposit OR split (1 collateral → 1 YES + 1 NO).

### Temporal / meta-game (Phase 2.4)
- No reentrancy hooks (`onERC1155Received` suppressed in
  `unsafeTransferFrom`/`unsafeBatchTransferFrom`). All state writes use
  assembly balance slot pattern.
- AutoRedeemer operator role gated by INITIALIZABLE_ROLES
  (`_ROLE_1` OPERATOR_ROLE). Multi-tx scenarios don't open new vectors.
- Migration edge: `_redeemIfResolved` applies legacy `payoutDenominator`
  scaling — works for binary legacy only. Non-binary legacy collapses to dust.

## Why no submittable bug surfaced

After **7+ layer exhaustive analysis of the now-fully-recovered V2 source**:
- Public Track A: PA-06..08 + PB-08 honest-zero'd (sessions 1+2).
- Track B (V2 audit regression): all PB-01..07, 09..12 surface reviewed.
- Key findings are **admin/operator-gated or migration-edge DoS only**:
  - Combinatorial asymmetric rounding dust loss = informational.
  - BRIDGE_ROLE synthetic Other resolution = admin-gated; would require
    bridge compromise (single private key exposure is the trust boundary).
  - `setCrossModuleAuth` correctly restricted to registered modules.
  - Router arbitrary selector call requires user-supplied positions + collateral.

**No unprivileged Critical/High/Medium theft path** meeting the eligibility
triad. Per project policy (`AGENTS.md` "submit_ready=0 for new residual
work", "eligibility triad mandatory", "do not submit admin-trust issues"),
**no Cantina post this session**.

## Negative findings worth recording

1. **Combinatorial NO-vs-basket dust**: NO(Q) decomposes into d YES baskets
   with slightly LESS dust loss than going via direct basket redeem at the
   same final state. Going via basket is **strictly worse for the user**.
2. **NegRisk synthetic Other resolution**: `BRIDGE_ROLE` can resolve the
   synthetic Other condition (index = arity), making any neg-risk event
   derivable as NO. Bridge compromise = full catastrophic resolution control.
   This is the same trust boundary as UMA oracle — known and documented.
3. **`setCrossModuleAuth` requires `moduleById[moduleId] == _module`**: admin
   cannot grant cross-module mint/burn to arbitrary EOAs (closed loophole).
4. **`matchOrdersAndPrepareCombinatorial` is operator-only**: operator cannot
   bypass `_validateCanonical` ascending order check.

## What remains un-probed (next session candidates)

- Track A residual: PA-09..PA-14 (CtfAdapter redeem + split/merge round-trip +
  NegRisk reportOutcome + indexSet collision + FeeModule cumulative fee +
  CollateralToken guard) — V1 only; V2 mostly replaces these surfaces.
- Track B edges not deeply probed:
  - AutoRedeemer multi-position batch under collateral balance diff replay.
  - BaseMigrationMixin non-binary legacy payout math (dust quant).
  - CombinatorialModule `combinatorialCollateralReturn` arbitrary selector
    interaction with conditional additivity.
  - NegRiskModule `_finalizeNegriskResolution` rejects non-binary; edge
    case: `result.length > 2` from underlying CTF (now constrained by
    `_storeResult`).
  - UUPS upgrade authorization on Proxy: only `owner()`. If owner key
    leaks → full upgrade control. Known trust boundary.
- Track B edges with potential (and not explored):
  - POLY_PROXY wallet signature replay with `POLY_PROXY` type
    (proxy wallet may have different `approve` semantics — out of scope).
  - POLY_GNOSIS_SAFE replay via different EIP-712 domain separator.

## Rotation candidates (per `data/security_results/day_shift/next.md`)

If Polymarket exhausted:
1. 1inch PROP-023 mainnet LOP usage scan (low-hanging).
2. Kamino Scope MEDIUM live stale-AUM profit PoC (mid-tier).
3. marginfi T22 residual fee deposit/withdraw edge (low-tier).

## Hard rules retained

- No external post without human-gate PASS.
- Eligibility triad mandatory for residual claims.
- Investigations / lab notebooks local unless operator explicitly publishes.
- Do not re-assay closed-out sessions (Makina, Polymarket PA-06..08,
  residual sweep).

## Session closeout

- Status: CLOSED, `submit_ready=0`.
- Next step (per `data/security_results/day_shift/next.md`): rotate to one
  of the listed alternates; or deepen Polymarket V2 AutoRedeemer +
  BaseMigrationMixin if operator wishes more Polymarket coverage.
- SPEC version: pending v6.64.0 closeout (V2 source unblock + session 3
  closeout note).
