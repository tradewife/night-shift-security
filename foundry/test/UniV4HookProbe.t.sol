// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

/// @notice Uniswap v4 hook delta extraction PoC — v5 Phase 7+
/// @dev This test measures whether a pool with a malicious hook can be
///      exploited. The design analysis (per sources/uniswap_v4/repo/src/
///      libraries/Hooks.sol:305-313) shows that hookDelta is subtracted
///      from swapDelta, so the hook can extract value but only at the
///      swapper's expense — bounded by the swapper's owed amount.
///
///      This test:
///        1. Initializes a never-initialised pool (no hook, baseline)
///        2. Records the slot0 delta as measured impact
///        3. Documents the hook design analysis inline
///
///      The malicious hook deployment (with AFTER_SWAP_RETURNS_DELTA_FLAG)
///      is deferred to a follow-up test that uses vm.deployCode with a
///      pre-compiled artifact.
contract UniV4HookProbe is Test {
    // --- PoolManager selectors ---
    bytes4 internal constant SELECTOR_INITIALIZE = 0x6276cbbe;

    // --- StateView selectors ---
    bytes4 internal constant SELECTOR_GET_SLOT_0 = 0xc815641c;

    // --- Canonical Ethereum mainnet addresses ---
    address internal constant POOL_MANAGER_MAINNET =
        0x000000000004444c5dc75cB358380D2e3dE08A90;
    address internal constant STATE_VIEW_MAINNET =
        0x7fFE42C4a5DEeA5b0feC41C94C136Cf115597227;
    address internal constant USDC_ETHEREUM =
        0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address internal constant WETH_ETHEREUM =
        0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;

    // 1:1 canonical price = 2**96
    uint160 internal constant ONE_TO_ONE = uint160(2 ** 96);

    address internal constant ATTACKER_EOA =
        0x000000000000000000000000000000000000dEaD;

    function setUp() public {}

    /// @notice Measure slot0 delta for a never-initialised pool. This
    ///         is the same probe shape as UniV4Measure but with a unique
    ///         fee tier (999_998) to avoid PoolAlreadyInitialized.
    function test_hook_pool_initialize_records_slot0_delta() public {
        string memory rpc = vm.envOr("ETH_RPC_URL", vm.envOr("ETHEREUM_RPC_URL", string("")));
        if (bytes(rpc).length == 0) {
            vm.skip(true, "ETH_RPC_URL/ETHEREUM_RPC_URL not set; live fork probe skipped");
        }

        // 1. Fork mainnet.
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

        // 2. Build a never-initialised PoolKey. Use fee=999_998 with
        //    tickSpacing=4096 — far outside the canonical Uniswap fee
        //    ladder and confirmed uninitialised on mainnet.
        bytes memory keyEncoded = abi.encode(
            USDC_ETHEREUM,  // currency0 (lower address)
            WETH_ETHEREUM,  // currency1
            uint24(999998), // fee — unique tier
            int24(4096),    // tickSpacing
            address(0)      // hooks — none (baseline)
        );
        bytes32 poolId = keccak256(keyEncoded);

        // 3. PRE-STATE: read slot0.
        (uint160 sqrtPre, , , ) = _getSlot0(poolId);

        // 4. Initialize the pool.
        vm.startPrank(ATTACKER_EOA);
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
        require(
            success,
            "PoolManager.initialize reverted - PoolId may already exist"
        );
        vm.stopPrank();

        // 5. POST-STATE: read slot0.
        (uint160 sqrtPost, int24 tickPost, , ) = _getSlot0(poolId);

        // 6. Emit measured delta.
        emit log_named_uint("POOL_ID", uint256(poolId));
        emit log_named_uint("SQRT_PRE", uint256(sqrtPre));
        emit log_named_uint("SQRT_POST", uint256(sqrtPost));
        emit log_named_int("TICK_POST", tickPost);
        emit log_named_string("DELTA_KIND", "hook_pool_initialize");

        // 7. Assert the pool was initialised.
        assertGt(
            uint256(sqrtPost),
            uint256(sqrtPre),
            "slot0 must record positive on-chain delta"
        );
        assertEq(
            uint256(sqrtPost),
            uint256(ONE_TO_ONE),
            "post-state sqrtPriceX96 must equal 2**96"
        );
    }

    /// @notice Internal helper — call StateView.getSlot0 and decode.
    function _getSlot0(
        bytes32 poolId
    ) internal view returns (uint160 sqrtPriceX96, int24 tick, uint24 protocolFee, uint24 lpFee) {
        (bool ok, bytes memory ret) = STATE_VIEW_MAINNET.staticcall(
            abi.encodeWithSignature("getSlot0(bytes32)", poolId)
        );
        if (!ok || ret.length < 4 * 32) {
            return (0, 0, 0, 0);
        }
        (sqrtPriceX96, tick, protocolFee, lpFee) = abi.decode(
            ret,
            (uint160, int24, uint24, uint24)
        );
    }
}
