# Attempt 2 — Active Bin Advancement + Liquidity Extraction (Meteora DLMM)

**Strategy:** Executable fuzz on state transition integrity during swap operations.
**Fresh perspective:** NOT thinking about fees. Thinking about the active bin cursor that advances through bins as swaps happen. What happens at bin boundaries? When liquidity is depleted mid-swap?

## Hypothesis

The swap loop advances through bins consuming liquidity. When a bin's liquidity runs out, advance_active_bin moves to the next bin. Could a corrupted bin array bitmap cause a swap to "skip" a bin with liquidity, extracting tokens at a stale (favorable) price?

## Source anchors

- `commons/src/extensions/lb_pair.rs` — `advance_active_bin()`
- `commons/src/extensions/bin.rs` — per-bin swap logic
- `commons/src/extensions/bin_array.rs` — bin lookup, bitmap walking

## Analysis

`advance_active_bin` moves active_id by +/-1 per bin depletion. Bounds check at MIN_BIN_ID/MAX_BIN_ID. A single swap can traverse multiple bins via the orchestration loop.

The bitmap tracks which bins have liquidity (U1024 bitmap, 256 bins per array). The `next_bin_array_index_with_liquidity_internal` function walks the bitmap to find the next non-empty bin array.

### Can a user manipulate the bitmap?

The bin array bitmap is updated by the protocol when liquidity is added/removed. It is NOT user-writable directly — it's part of the LbPair state that only the program mutates via add_liquidity/remove_liquidity instructions.

### Can a swap "skip" a bin?

The per-bin swap logic in `bin.rs` processes one bin at a time. When the active bin's liquidity runs out, the orchestration advances to the next bin. The bitmap is used to SKIP EMPTY BIN ARRAYS (groups of 70 bins), not individual bins within an array.

**Key insight:** Within a single bin array, the swap walks bins sequentially. The bitmap only optimizes bin-array-level traversal. An individual bin with liquidity cannot be skipped.

### Empty bin edge case

If active_id points at a bin with zero liquidity, the swap immediately advances. No tokens are exchanged at that price level (zero liquidity = zero output). No value extraction.

### Concurrent swaps

Two swaps in the same slot process sequentially on Solana. The first swap's state changes (advanced active_id, depleted liquidity) are visible to the second swap. This is by design — the active bin is shared state. A MEV searcher could sandwich by observing the first swap's bin advancement, but this is standard AMM MEV, not a vulnerability.

## Verdict

**FALSIFIED.** The active bin cursor advances monotonically by 1 per bin depletion. Empty bins are skipped harmlessly. The bitmap tracks liquidity presence at the array level, not individual bins. No stale-price extraction possible.

## Category

**False positive** — the bin advancement logic is structurally correct. The cursor is protocol-controlled, advances monotonically, and empty bins have zero swap impact.
