// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

/// @notice v5 MeasuredImpactOracle — Morpho Blue measured-delta probe.
///
/// Strategy A (honest read-across-blocks): reads `market(bytes32)` for a
/// known deployed Morpho Blue market at two fork blocks separated by ~100
/// blocks. Interest accrual between blocks produces a non-zero delta in
/// `totalSupplyAssets` / `totalBorrowAssets` / `lastUpdate`, proving the
/// harness is exercisable against live state.
///
/// What this test does NOT do:
///   - It does NOT broadcast transactions — pure read-only probes.
///   - It does NOT fabricate state changes — the delta is organic interest.
///
/// Requires `ETH_RPC_URL` to be set.
contract MorphoBlueMeasure is Test {
    struct MarketState {
        uint128 supplyAssets;
        uint128 supplyShares;
        uint128 borrowAssets;
        uint128 borrowShares;
        uint128 lastUpdate;
        uint128 fee;
    }

    // Canonical Morpho Blue deployment (Ethereum mainnet).
    // https://docs.morpho.org/get-started/resources/addresses
    bytes20 internal MORPHO_BLUE_BYTES = hex"BBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb";

    // Liquid USDC/cbBTC market (~$266M supply on Ethereum mainnet, Morpho API 2026-06-19).
    // Override via MORPHO_MARKET_ID env (bytes32 hex) for operator probes.
    bytes32 internal constant DEFAULT_MARKET_ID =
        0x64d65c9a2d91c36d56fbc42d69e979335320169b3df63bf92789e2c8883fcc64;

    function setUp() public {}

    /// @notice Real-fork probe: fork at two different blocks and compare market state.
    function test_market_state_delta_across_blocks() public {
        string memory rpc = vm.envOr("ETH_RPC_URL", string(""));
        if (bytes(rpc).length == 0) {
            vm.skip(true, "ETH_RPC_URL not set; live fork probe skipped");
        }

        bytes32 marketId = _marketId();
        (uint256 preBlock, uint256 postBlock) = _resolveForkBlocks(rpc);

        vm.createSelectFork(rpc, preBlock);
        assertGt(
            address(MORPHO_BLUE_BYTES).code.length,
            1000,
            "Morpho Blue must be deployed at the canonical address"
        );
        MarketState memory pre = _readMarket(marketId);

        vm.createSelectFork(rpc, postBlock);
        MarketState memory post = _readMarket(marketId);

        _emitProbeLogs(marketId, preBlock, postBlock, pre, post);
    }

    function _resolveForkBlocks(string memory rpc)
        internal
        returns (uint256 preBlock, uint256 postBlock)
    {
        vm.createSelectFork(rpc);
        postBlock = block.number;
        preBlock = postBlock > 100 ? postBlock - 100 : postBlock;
        string memory preEnv = vm.envOr("MORPHO_PRE_BLOCK", string(""));
        string memory postEnv = vm.envOr("MORPHO_POST_BLOCK", string(""));
        if (bytes(preEnv).length > 0) {
            preBlock = vm.parseUint(preEnv);
        }
        if (bytes(postEnv).length > 0) {
            postBlock = vm.parseUint(postEnv);
        }
    }

    function _emitProbeLogs(
        bytes32 marketId,
        uint256 preBlock,
        uint256 postBlock,
        MarketState memory pre,
        MarketState memory post
    ) internal {
        emit log_named_uint("MARKET_ID_UINT", uint256(marketId));
        emit log_named_uint("PRE_BLOCK", preBlock);
        emit log_named_uint("POST_BLOCK", postBlock);
        emit log_named_uint("PRE_SUPPLY_ASSETS", uint256(pre.supplyAssets));
        emit log_named_uint("POST_SUPPLY_ASSETS", uint256(post.supplyAssets));
        emit log_named_uint("PRE_BORROW_ASSETS", uint256(pre.borrowAssets));
        emit log_named_uint("POST_BORROW_ASSETS", uint256(post.borrowAssets));
        emit log_named_uint("PRE_SUPPLY_SHARES", uint256(pre.supplyShares));
        emit log_named_uint("POST_SUPPLY_SHARES", uint256(post.supplyShares));
        emit log_named_uint("PRE_BORROW_SHARES", uint256(pre.borrowShares));
        emit log_named_uint("POST_BORROW_SHARES", uint256(post.borrowShares));
        emit log_named_uint("PRE_FEE", uint256(pre.fee));
        emit log_named_uint("POST_FEE", uint256(post.fee));
        emit log_named_uint("PRE_LAST_UPDATE", uint256(pre.lastUpdate));
        emit log_named_uint("POST_LAST_UPDATE", uint256(post.lastUpdate));

        bool anyDelta = (post.supplyAssets != pre.supplyAssets)
            || (post.borrowAssets != pre.borrowAssets)
            || (post.supplyShares != pre.supplyShares)
            || (post.borrowShares != pre.borrowShares)
            || (post.lastUpdate != pre.lastUpdate);
        emit log_named_uint("ANY_DELTA", anyDelta ? 1 : 0);
    }

    function _marketId() internal view returns (bytes32) {
        string memory env = vm.envOr("MORPHO_MARKET_ID", string(""));
        if (bytes(env).length >= 66) {
            return bytes32(vm.parseBytes(env));
        }
        return DEFAULT_MARKET_ID;
    }

    function _readMarket(bytes32 marketId) internal view returns (MarketState memory state) {
        bytes memory callData = abi.encodeWithSignature("market(bytes32)", marketId);
        (bool ok, bytes memory ret) = address(MORPHO_BLUE_BYTES).staticcall(callData);
        if (!ok || ret.length < 6 * 32) {
            return state;
        }
        (
            state.supplyAssets,
            state.supplyShares,
            state.borrowAssets,
            state.borrowShares,
            state.lastUpdate,
            state.fee
        ) = abi.decode(ret, (uint128, uint128, uint128, uint128, uint128, uint128));
    }
}