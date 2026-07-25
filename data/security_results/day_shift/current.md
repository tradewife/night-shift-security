# Session plan — current

**Status: open (2026-07-16). 1inch sessions 8–10 residual. submit_ready=0. Keep hunting.**

> **Cross-target update (2026-07-24, closeout 2026-07-25 — v6.60.0):**
> Horizen ZEN Staking (`sources/horizen/repo @ ab92502`) NSS pass via 4d-chess-sequential.
> 16-test adversarial Foundry harness on RewardAccumulator ↔ ZenStaker primary subsystem.
> FINDING-001 (sub-threshold flush revert ~1-wei griefing) identified; out-of-scope
> per project's "permanent denial" carveout and SECURITY.md known-issue #1.
> **Horizen Session 1 closed (engine-level honest-zero, `submit_ready=0`).**
> Phase B re-evaluation mandatory 2026-07-27 if Immunefi scope/reward/config deltas appear.
> See `data/security_results/investigations/2026-07-24-horizen-zen-staking/` and lab notebook.
> **This day-shift session remains open in the 1inch arc below; Horizen parked pending Phase B.**

## Completed this arc

| Session | Surface | Executable | Result |
|---|---|---|---|
| 8 | limit-order-settlement | 33 tests (unit+edge+E2E fill) | honest-zero |
| 8b | LOP NativeOrder | 16 tests | honest-zero |
| 9a | EscrowDst fee/timestamp | 6 tests | honest-zero + **PROP-003 near-miss** |
| 9b | Solana fusion auction/fee unit | 9 cargo tests | honest-zero |
| 10a | Multi-fill pure math (PROP-016) | 5 tests + fuzz 1024 | honest-zero |
| 10b | SafeOrderBuilder formula (PROP-020) | 5 tests | design residual (Safe-owner params) |
| 10c | DutchAuctionCalculator edges | 6 tests | honest-zero (DoS if misconfig) |
| 10d | RangeAmountCalculator | 6 tests | honest-zero |
| 10e | **ERC721Proxy partial fill (PROP-023)** | **3 E2E PASS** | **candidate** — dust fill takes full NFT for fractional price |

**Totals:** 64 + 10 + 15 = **89** executable checks; **submit_ready candidate: PROP-023** (see caveats).

## Near-miss log (not submit_ready)

### PROP-003: `createDstEscrow` untrusted `srcCancellationTimestamp`

- On-chain check does **not** bind timestamp to real src escrow cancel time.
- Allows far-future `DstCancellation` via spoof.
- **README explicitly:** secret distribution + escrow verification are off-chain; publicWithdraw incentivizes other resolvers via safety deposit.
- Class: design residual / weak on-chain invariant under stated trust model — not forced Critical for correct off-chain secret handling.

### PROP-020: SafeOrderBuilder dust takingAmount

- Caller-supplied `originalAnswer` can floor taking to 0.
- Requires Safe **delegatecall** with owner-signed params — not unprivileged external path.
- Class: design residual / privileged path.

### PROP-023: ERC721Proxy ignores fill amount (candidate)

- E2E: fill `1` of `makingAmount=100` → full NFT to taker, pay `10/1000` DAI.
- Root: `func_60iHVgK` ignores `amount`; LOP still pro-rates price.
- Works under remaining **and** bit invalidator.
- **Caveat:** official docs/example set `makingAmount: 1`. No on-chain enforcement. Proxy permissionlessly deployable.
- PoC: `sources/1inch/harness-lop/test/NssERC721PartialFillE2E.t.sol`
- Writeup: `data/security_results/investigations/2026-07-16-1inch-smart-contracts/PROP023-erc721proxy-partial-fill.md`
- Gate: strengthen with production NFT LOP evidence using `makingAmount > 1`, or submit as incomplete-defense / High footgun.

## Night Shift handoff

Do not re-run green s8–s10a–d suites without new hypothesis.
**Priority:** promote PROP-023 (production usage scan + submission pack) **or** keep hunting unprivileged Critical without misconfig (Solana CPI, ChainlinkCalculator, Permit2 partial).
