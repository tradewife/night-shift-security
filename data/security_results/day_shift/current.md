# Session plan — current

**Status: open (2026-07-26). Rootstock PowPeg onboarding complete; strategy execution phase begins. submit_ready=0. Keep hunting.**

> **Cross-target closeout (2026-07-26 — v6.61.0, Rootstock PowPeg onboarding):**
> Rootstock PowPeg onboarding complete. rsk-powhsm@5.6.2, powpeg-node@VETIVER-9.0.3.0, rskj@VETIVER-9.0.3. Quarkslab SGX audit (9 findings) mapped. Codegraph-x-ray on Primary Subsystem (bc_advance+auth_tx+attestation+upgrade+Java signer) delivered 30 invariants + 22 property candidates + 9 strategies (≥70% Primary). Minimal harnesses built: C libFuzzer (bc_advance), Python (attestation middleware), Java JQF differential (signer message builder). rskj Bridge precompile codegraph (108 symbols). **submit_ready=0** — honest-zero start.
> Local artifacts only: `data/security_results/investigations/2026-07-25-rootstock-powpeg/`, `sources/rsk-powhsm/firmware/fuzz/`, `sources/powpeg-node/src/test/.../PowHSMSignerMessageBuilderDifferentialFuzzTest.java`.

> **Prior closeout (2026-07-25 — v6.60.2, Horizen Session 3 extended 4d-chess-sequential):**
> Horizen ZEN Staking (`sources/horizen/repo @ ab92502`) Session 3 endurance press closed.
> ~90+ new NSS Foundry tests (R3–R26) + live mainnet/testnet fork + frontend/subgraph/OFT/Binary.
> FINDING-001 refined (mid-stream dust blends; post-expiry temporary carveout). Empty-pool = known #7.
> **No submit-ready candidate. Engine-level honest-zero extended. `submit_ready=0`.**
> Local artifacts only: `data/security_results/investigations/2026-07-24-horizen-zen-staking/`,
> `sources/horizen/repo/test/NSSRound*.t.sol`, `watch-first-flush.sh`.
> **Horizen parked pending Phase B (2026-07-27) or live first-flush re-check.**
> This day-shift session remains open on the Rootstock PowPeg arc below.

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
**Do not re-open Horizen RA core** unless Phase B (2026-07-27) changes scope/config or first-flush live state shows attribution failure (`watch-first-flush.sh` → POST_FIRST_FLUSH then re-run mainnet fork claim-all).
**Priority:** promote PROP-023 (production usage scan + submission pack) **or** keep hunting unprivileged Critical without misconfig (Solana CPI, ChainlinkCalculator, Permit2 partial).
