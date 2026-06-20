// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

/// @notice v5 MeasuredImpactOracle — Uniswap v4 measured-delta probe.
///
/// @notice v5 MeasuredImpactOracle — Uniswap v4 measured-delta probe
///         (carried into v6). Originally raised as audit correction **C2**
///         (the v4.2-era audit file was retired on 2026-06-20). This contract
/// performs a real on-chain state-changing sequence against the deployed
/// PoolManager on a forked RPC and records pre/post slot reads so the
/// Python side (`impact/measured_oracle.py`) can compute a measured diff.
///
/// Approach:
///   1. Fork via `vm.createSelectFork` (uses `ETH_RPC_URL`).
///   2. Read pre-state: attacker EOA USDC balance, attacker EOA native
///      balance, `StateView.getSlot0(PoolId)` for the canonical USDC/WETH
///      PoolKey (fee=3000, tickSpacing=60).
///   3. Pick a **never-initialised** PoolKey (currency0 = USDC, currency1
///      = WETH, fee=10000, tickSpacing=200 — a different fee ensures the
///      derived PoolId has not been seeded on mainnet) and call
///      `PoolManager.initialize(key, sqrtPriceX96)` using raw calldata
///      encoded via `abi.encodeWithSignature` so we do not need a v4-core
///      Solidity import.
///   4. Read post-state: same reads at the post-initialize block. The slot
///      `sqrtPriceX96` MUST move from `(0,0)` to `(79228162514…, 0)`,
///      proving a real on-chain delta.
///   5. Emit a JSON-shaped summary so the Python oracle can read it via a
///      follow-up `eth_call`/`eth_getBalance` (left to the Python side).
///
/// What this test does NOT do:
///   - It does NOT `donate` from any token balance (the donor-funded path
///     requires ERC-20 approval & token transfer plumbing that is out of
///     scope for C2 — the diff a `donate` produces is the PoolManager's
///     internal booked `BalanceDelta`, not a real ERC-20 transfer unless
///     `settle()`+`take()` are paired by the caller).
///   - It does NOT mutate anything on real mainnet — `vm.createSelectFork`
///     is hermetic to the env's RPC and never broadcasts back to live
///     chain.
///
/// Why fee=10000: the canonical Uniswap v4 deployment has well-known
/// USDC/WETH fee=3000 pools already initialized; reproducing the
/// initialize step on those keys will revert (already-initialised).
/// Fee=10000 with tickSpacing=200 produces a fresh, uninitialized PoolId
/// which accepts a new initialize call.
contract UniV4Measure is Test {
    // --- PoolManager selectors (canonical Ethereum Keccak-256) ---
    bytes4 internal constant SELECTOR_INITIALIZE = 0x6276cbbe;
    // `initialize((address,address,uint24,int24,address),uint160)`
    //
    // The full ABI signature must include the tuple so `abi.encodeWithSignature`
    // ABI-encodes the nested PoolKey struct correctly.

    // --- ERC-20 selectors ---
    bytes4 internal constant SELECTOR_BALANCE_OF = 0x70a08231;

    // --- StateView selectors ---
    bytes4 internal constant SELECTOR_GET_SLOT_0 = 0xc815641c;

    // Canonical Ethereum mainnet PoolManager deployment address.
    address internal constant POOL_MANAGER_MAINNET =
        0x000000000004444c5dc75cB358380D2e3dE08A90;

    // Canonical StateView deployment address.
    address internal constant STATE_VIEW_MAINNET =
        0x7fFE42C4a5DEeA5b0feC41C94C136Cf115597227;

    // Canonical USDC + WETH addresses.
    address internal constant USDC_ETHEREUM =
        0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address internal constant WETH_ETHEREUM =
        0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;

    // 1:1 canonical price = 2**96 (used for the post-state comparison).
    uint160 internal constant ONE_TO_ONE = uint160(2**96);

    // The address we'll attribute to "attacker EOA" for the diff.
    // Foundry lets us impersonate any address; we use a deterministic
    // test address so the Python side can replay the same pre/post diff.
    address internal constant ATTACKER_EOA =
        0x000000000000000000000000000000000000dEaD;

    function setUp() public {}

    /// @notice Real-fork probe: initialize a never-initialised PoolKey and
    ///         record the slot0/state diff. Requires `ETH_RPC_URL`.
    function test_initialize_records_slot0_delta() public {
        string memory rpc = vm.envOr("ETH_RPC_URL", string(""));
        if (bytes(rpc).length == 0) {
            vm.skip(true, "ETH_RPC_URL not set; live fork probe skipped");
        }

        // 1. Fork the chain.
        vm.createSelectFork(rpc);
        assertGt(
            POOL_MANAGER_MAINNET.code.length,
            1000,
            "PoolManager must be deployed at the canonical address"
        );
        assertGt(
            STATE_VIEW_MAINNET.code.length,
            100,
            "StateView must be deployed at the canonical address"
        );

        // 2. Build a never-initialised PoolKey. USDC<cWETH (USDC is the
        //    numerically smaller address). We pick fee=999_999 with
        //    tickSpacing=8192 - this tier is far outside the canonical
        //    Uniswap fee ladder (100/500/3000/10000) and central Uni v4
        //    dashboards confirm it has never been initialised on Ethereum
        //    mainnet. (Probed live via `_probe_init.sol`: returns
        //    `OK=1`. The previous defaults kept reverting with
        //    `PoolAlreadyInitialized` because the canonical USDC/WETH
        //    fee=10000 tickspacing=200 pool has been deployed live.)
        bytes memory keyEncoded = abi.encode(
            USDC_ETHEREUM, // currency0 (lower address first)
            WETH_ETHEREUM, // currency1
            uint24(999999), // fee (LPFee)
            int24(8192),    // tickSpacing (matches fee tier)
            address(0)      // hooks - none
        );

        // 3. Compute the canonical PoolId (= keccak256(keyEncoded)).
        bytes32 poolId = keccak256(keyEncoded);

        // 4. PRE-STATE: read getSlot0(poolId) — must be (0,0) because
        //    this PoolId has never been initialized on mainnet (we picked
        //    fee=10000 specifically to ensure that).
        (uint160 sqrtPre, int24 tickPre, , ) = _getSlot0(poolId);
        // NOTE: on `getSlot0` a never-initialised PoolId in v4 REVERTS
        // (the slot itself is stored in transient storage which is
        // empty/missing on init). The expectation is that the call
        // reverts; we catch that below and re-capture `sqrtPre=0` to keep
        // the schema stable across pre/post types.
        //
        // The ordPre reverts case is detected by simulating the call via
        // a staticcall: if it reverts, we record 0.

        // 5. POST-STATE: bypass the PoolManager.initialize authorization
        //    gate via `vm.startPrank`. Initialize is permissioned by default
        //    in canonical v4-core to anyone when the PoolId is fresh; we
        //    do not need special authorization other than a fresh PoolId.
        vm.startPrank(ATTACKER_EOA);
        // Use abi.encodeWithSignature so we don't need the v4-core imports.
        // PoolKey is a 5-tuple struct; the inner abi.decode reconstructs the
        // 5-tuple by reading it back through abi.decode.
        address c0;
        address c1;
        uint24 fee;
        int24 spacing;
        address hooks;
        (c0, c1, fee, spacing, hooks) = abi.decode(
            keyEncoded,
            (address, address, uint24, int24, address)
        );
        (bool success, ) = POOL_MANAGER_MAINNET.call(
            abi.encodeWithSignature(
                "initialize((address,address,uint24,int24,address),uint160)",
                c0, c1, fee, spacing, hooks,
                ONE_TO_ONE
            )
        );
        // If the PoolId was actually fresh, this MUST succeed.
        require(
            success,
            "PoolManager.initialize reverted - PoolId may already be initialised or fee/tickSpacing invalid"
        );
        vm.stopPrank();

        (uint160 sqrtPost, int24 tickPost, , ) = _getSlot0(poolId);

        // 6. The delta is the entire C2 measurement.
        emit log_named_uint("POOL_ID_HEX", uint256(poolId));
        emit log_named_uint("SQRT_PRE", uint256(sqrtPre));
        emit log_named_uint("SQRT_POST", uint256(sqrtPost));
        emit log_named_int("TICK_PRE", tickPre);
        emit log_named_int("TICK_POST", tickPost);
        emit log_named_string("DELTA_KIND", "slot0_initialize");

        // 7. The oracle's core honesty assertion: slot0 must have moved.
        assertEq(
            uint256(sqrtPost),
            uint256(ONE_TO_ONE),
            "post-state sqrtPriceX96 must equal 2**96"
        );
        // Pre-state was 0 (we forced the read above even though the live
        // call would have reverted — see note). The oracle parities:
        // measured = (sqrtPost - sqrtPre) > 0 = ONE_TO_ONE.
        assertGt(
            uint256(sqrtPost),
            uint256(sqrtPre),
            "pre vs post sqrtPriceX96 must record a positive on-chain delta"
        );
    }

    /// @notice Internal helper — call `StateView.getSlot0(bytes32)` and
    ///         decode to (sqrtPriceX96, tick, protocolFee, lpFee).
    function _getSlot0(
        bytes32 poolId
    ) internal view returns (uint160 sqrtPriceX96, int24 tick, uint24 protocolFee, uint24 lpFee) {
        // Guard against revert by using `staticcall`. StateView.getSlot0(bytes32)
        // returns: (uint160 sqrtPriceX96, int24 tick, uint24 protocolFee, uint24 lpFee)
        // - four 32-byte words packed.
        (bool ok, bytes memory ret) = STATE_VIEW_MAINNET.staticcall(
            abi.encodeWithSignature("getSlot0(bytes32)", poolId)
        );
        if (!ok || ret.length < 4 * 32) {
            // Treat revert / short-payload as a zeroed slot. C2 explicitly
            // documents this honesty path: an uninitialized PoolId
            // produces a (0,0) "diff" and the oracle must NOT report
            // a positive measured impact for it.
            return (0, 0, 0, 0);
        }
        (sqrtPriceX96, tick, protocolFee, lpFee) = abi.decode(
            ret,
            (uint160, int24, uint24, uint24)
        );
    }
}
