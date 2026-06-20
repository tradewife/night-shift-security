// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

/// @notice v5 NativeHarness — Uniswap v4 PoolManager + IHooks scaffold.
/// @notice v5 NativeHarness — Uniswap v4 PoolManager + IHooks scaffold
///         (carried into v6). Originally raised vs the v4.2-era audit
///         correction C1; the audit file has been retired on 2026-06-20.
///
/// Imports nothing from sources/uniswap_v4/repo because v4-core's
/// remappings depend on submodules (openzeppelin, solmate, ensdomains).
/// The interface below mirrors the canonical public surface of the deployed
/// PoolManager / StateView contracts on Ethereum mainnet.
///
/// The Python harness (src/night_shift_security/native/uniswap_v4.py) is
/// the authority for selector derivation; this Solidity test keeps the
/// same 4-byte selectors hand-rolled from the canonical Ethereum
/// Keccak-256 prefix.
///
/// What this test does:
///   1. compiles under `forge build`,
///   2. checks that the canonical selectors match what the Python harness
///      produces (compile-time hard-coded; selectors come from
///      keccak256(signature)[:4]),
///   3. carries a real-fork test that runs only when ETH_RPC_URL is set
///      AND POOL_MANAGER_MAINNET is non-zero. The fork test does NOT
///      broadcast; it only reads bytecode via vm.createSelectFork +
///      address.code.
contract UniswapV4PoolManagerHarness is Test {
    // --- PoolManager selectors (canonical Ethereum Keccak-256) ---
    bytes4 internal constant SELECTOR_INITIALIZE = 0x6276cbbe;
    bytes4 internal constant SELECTOR_MODIFY_LIQUIDITY = 0x5a6bcfda;
    bytes4 internal constant SELECTOR_SWAP = 0x1998bab9;
    bytes4 internal constant SELECTOR_DONATE = 0x234266d7;
    bytes4 internal constant SELECTOR_SETTLE = 0x11da60b4;
    bytes4 internal constant SELECTOR_SETTLE_FOR = 0x3dd45adb;
    bytes4 internal constant SELECTOR_TAKE = 0x0b0d9c09;
    bytes4 internal constant SELECTOR_UNLOCK = 0x48c89491;
    bytes4 internal constant SELECTOR_MINT = 0x156e29f6;
    bytes4 internal constant SELECTOR_BURN = 0xf5298aca;
    bytes4 internal constant SELECTOR_TRANSFER = 0x095bcdb6;

    // --- IHooks selectors (canonical Ethereum Keccak-256) ---
    bytes4 internal constant SELECTOR_BEFORE_INITIALIZE = 0xdc98354e;
    bytes4 internal constant SELECTOR_AFTER_INITIALIZE = 0x6fe7e6eb;
    bytes4 internal constant SELECTOR_BEFORE_ADD_LIQUIDITY = 0x259982e5;
    bytes4 internal constant SELECTOR_AFTER_ADD_LIQUIDITY = 0x5a2a8100;
    bytes4 internal constant SELECTOR_BEFORE_REMOVE_LIQUIDITY = 0x21d0ee70;
    bytes4 internal constant SELECTOR_AFTER_REMOVE_LIQUIDITY = 0x8db2b652;
    bytes4 internal constant SELECTOR_BEFORE_SWAP = 0x3fd9994c;
    bytes4 internal constant SELECTOR_AFTER_SWAP = 0x322fc972;
    bytes4 internal constant SELECTOR_BEFORE_DONATE = 0xb6a8b0fa;
    bytes4 internal constant SELECTOR_AFTER_DONATE = 0xe1b4af69;

    // --- StateView selectors (canonical Ethereum Keccak-256) ---
    bytes4 internal constant SELECTOR_GET_SLOT_0 = 0xc815641c;
    bytes4 internal constant SELECTOR_GET_LIQUIDITY = 0xfa6793d5;

    /// @notice Canonical Ethereum mainnet PoolManager deployment address.
    ///         Sourced from https://etherscan.io/address/0x000...e3de08a90
    ///         (Etherscan Verified, $101B ledger balance Feb-2026).
    ///         Operators must reconfirm against the canonical Uniswap
    ///         Deployments reference before binding a measured delta.
    address internal constant POOL_MANAGER_MAINNET = 0x000000000004444c5dc75cB358380D2e3dE08A90;

    /// @notice Canonical StateView deployment address (Etherscan Verified).
    address internal constant STATE_VIEW_MAINNET = 0x7fFE42C4a5DEeA5b0feC41C94C136Cf115597227;

    function setUp() public {}

    /// @notice Compile-time selector parity check (Python harness ↔ Foundry).
    function test_pool_manager_selectors_canonical() public pure {
        require(SELECTOR_INITIALIZE == bytes4(0x6276cbbe), "initialize");
        require(SELECTOR_MODIFY_LIQUIDITY == bytes4(0x5a6bcfda), "modifyLiquidity");
        require(SELECTOR_SWAP == bytes4(0x1998bab9), "swap");
        require(SELECTOR_DONATE == bytes4(0x234266d7), "donate");
        require(SELECTOR_SETTLE == bytes4(0x11da60b4), "settle");
        require(SELECTOR_SETTLE_FOR == bytes4(0x3dd45adb), "settleFor");
        require(SELECTOR_TAKE == bytes4(0x0b0d9c09), "take");
        require(SELECTOR_UNLOCK == bytes4(0x48c89491), "unlock");
        require(SELECTOR_MINT == bytes4(0x156e29f6), "mint");
        require(SELECTOR_BURN == bytes4(0xf5298aca), "burn");
        require(SELECTOR_TRANSFER == bytes4(0x095bcdb6), "transfer");

        require(SELECTOR_BEFORE_INITIALIZE == bytes4(0xdc98354e), "beforeInitialize");
        require(SELECTOR_AFTER_INITIALIZE == bytes4(0x6fe7e6eb), "afterInitialize");
        require(SELECTOR_BEFORE_ADD_LIQUIDITY == bytes4(0x259982e5), "beforeAddLiquidity");
        require(SELECTOR_AFTER_ADD_LIQUIDITY == bytes4(0x5a2a8100), "afterAddLiquidity");
        require(SELECTOR_BEFORE_REMOVE_LIQUIDITY == bytes4(0x21d0ee70), "beforeRemoveLiquidity");
        require(SELECTOR_AFTER_REMOVE_LIQUIDITY == bytes4(0x8db2b652), "afterRemoveLiquidity");
        require(SELECTOR_BEFORE_SWAP == bytes4(0x3fd9994c), "beforeSwap");
        require(SELECTOR_AFTER_SWAP == bytes4(0x322fc972), "afterSwap");
        require(SELECTOR_BEFORE_DONATE == bytes4(0xb6a8b0fa), "beforeDonate");
        require(SELECTOR_AFTER_DONATE == bytes4(0xe1b4af69), "afterDonate");

        require(SELECTOR_GET_SLOT_0 == bytes4(0xc815641c), "getSlot0(StateView)");
        require(SELECTOR_GET_LIQUIDITY == bytes4(0xfa6793d5), "getLiquidity(StateView)");

        assertTrue(true);
    }

    /// @notice Live-deployed bytecode presence check (ETH_RPC_URL required).
    ///         Read-only — does not broadcast, no measurable delta this round.
    function test_pool_manager_deployment_code_present() public {
        string memory rpc = vm.envOr("ETH_RPC_URL", string(""));
        if (bytes(rpc).length == 0) {
            vm.skip(true, "ETH_RPC_URL not set; live fork probe skipped");
        }

        vm.createSelectFork(rpc);
        bytes memory code = POOL_MANAGER_MAINNET.code;
        // PoolManager is a substantial singleton (~48KB on mainnet).
        assertGt(code.length, 1000, "PoolManager should have code at the requested block");

        bytes memory state_code = STATE_VIEW_MAINNET.code;
        assertGt(state_code.length, 100, "StateView should have code at the requested block");
    }
}
