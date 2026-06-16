// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

interface IERC20Balance {
    function balanceOf(address account) external view returns (uint256);
}

interface IWormholeTokenBridgeValueProbe {
    function completeTransfer(bytes memory encodedVm) external;
    function outstandingBridged(address token) external view returns (uint256);
}

/// @title WormholeValueProbe - deployed-state negative value-movement probes
contract WormholeValueProbeTest is Test {
    string constant ETHEREUM_RPC = "ETHEREUM_RPC_URL";

    address constant WORMHOLE_TOKEN_BRIDGE = 0x3ee18B2214AFF97000D974cf647E7C347E8fa585;
    address constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant ATTACKER = address(0xA77AcC);

    function _forkOrSkip(string memory rpcEnv, uint256 blockNumber) internal {
        try vm.envString(rpcEnv) returns (string memory rpc) {
            if (blockNumber == 0) {
                vm.createSelectFork(rpc);
            } else {
                vm.createSelectFork(rpc, blockNumber);
            }
        } catch {
            vm.skip(true);
        }
    }

    /// @notice Invalid completion payload must not release locked native-chain assets.
    function testForkWormholeInvalidCompleteTransferNoUsdcDelta() public {
        _forkOrSkip(ETHEREUM_RPC, vm.envOr("FORK_BLOCK_NUMBER", uint256(0)));

        IERC20Balance usdc = IERC20Balance(USDC);
        IWormholeTokenBridgeValueProbe bridge = IWormholeTokenBridgeValueProbe(WORMHOLE_TOKEN_BRIDGE);

        uint256 bridgeBefore = usdc.balanceOf(WORMHOLE_TOKEN_BRIDGE);
        uint256 attackerBefore = usdc.balanceOf(ATTACKER);
        uint256 outstandingBefore = bridge.outstandingBridged(USDC);
        assertGt(bridgeBefore, 0, "live bridge must hold USDC");
        assertGt(outstandingBefore, 0, "live bridge must track USDC outstanding");

        vm.prank(ATTACKER);
        vm.expectRevert();
        bridge.completeTransfer(hex"01000000");

        uint256 bridgeAfter = usdc.balanceOf(WORMHOLE_TOKEN_BRIDGE);
        uint256 attackerAfter = usdc.balanceOf(ATTACKER);
        uint256 outstandingAfter = bridge.outstandingBridged(USDC);

        assertEq(bridgeAfter, bridgeBefore, "invalid VAA changed bridge USDC balance");
        assertEq(attackerAfter, attackerBefore, "invalid VAA paid attacker");
        assertEq(outstandingAfter, outstandingBefore, "invalid VAA changed outstanding USDC");

        console2.log("WORMHOLE_VALUE_PROBE:invalid_complete_transfer");
        console2.log("BRIDGE_USDC_BALANCE:%s", bridgeAfter);
        console2.log("OUTSTANDING_USDC:%s", outstandingAfter);
        console2.log("TOKEN_DELTA:0");
        console2.log("DELTA_WEI:0");
        console2.log("BRIDGE_ACCOUNTING_VIOLATION:0");
        console2.log("TRIAGE_SURFACE_VERIFIED:1");
        console2.log("TRIAGE_SURFACE_REQUIRES_MEASURED_DELTA:1");
    }
}
