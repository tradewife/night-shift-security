// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

interface IERC20Balance {
    function balanceOf(address account) external view returns (uint256);
}

interface IWormholeTokenBridgeValueProbe {
    function completeTransfer(bytes memory encodedVm) external;
    function bridgeContracts(uint16 chainId) external view returns (bytes32);
    function chainId() external view returns (uint16);
    function outstandingBridged(address token) external view returns (uint256);
    function wormhole() external view returns (address);
}

/// @title WormholeValueProbe - deployed-state negative value-movement probes
contract WormholeValueProbeTest is Test {
    string constant ETHEREUM_RPC = "ETHEREUM_RPC_URL";

    address constant WORMHOLE_TOKEN_BRIDGE = 0x3ee18B2214AFF97000D974cf647E7C347E8fa585;
    address constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant ATTACKER = address(0xA77AcC);

    struct Signature {
        bytes32 r;
        bytes32 s;
        uint8 v;
        uint8 guardianIndex;
    }

    struct VM {
        uint8 version;
        uint32 timestamp;
        uint32 nonce;
        uint16 emitterChainId;
        bytes32 emitterAddress;
        uint64 sequence;
        uint8 consistencyLevel;
        bytes payload;
        uint32 guardianSetIndex;
        Signature[] signatures;
        bytes32 hash;
    }

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

    /// @notice Harnessed signed-message baseline: mocked core verification exercises deployed bridge accounting.
    function testForkWormholeMockAuthorizedCompleteTransferMovesUsdcBaseline() public {
        _forkOrSkip(ETHEREUM_RPC, vm.envOr("FORK_BLOCK_NUMBER", uint256(0)));

        IERC20Balance usdc = IERC20Balance(USDC);
        IWormholeTokenBridgeValueProbe bridge = IWormholeTokenBridgeValueProbe(WORMHOLE_TOKEN_BRIDGE);

        uint16 sourceChain = 1;
        uint16 targetChain = bridge.chainId();
        bytes32 sourceEmitter = bridge.bridgeContracts(sourceChain);
        assertTrue(sourceEmitter != bytes32(0), "source emitter must be registered");
        assertEq(targetChain, 2, "Ethereum Wormhole chain id");

        uint256 bridgeBefore = usdc.balanceOf(WORMHOLE_TOKEN_BRIDGE);
        uint256 attackerBefore = usdc.balanceOf(ATTACKER);
        uint256 outstandingBefore = bridge.outstandingBridged(USDC);
        uint256 amount = 1_000_000;
        assertGe(bridgeBefore, amount, "live bridge must hold probe USDC");
        assertGe(outstandingBefore, amount, "live outstanding must cover probe USDC");

        bytes memory payload = abi.encodePacked(
            uint8(1),
            amount,
            bytes32(uint256(uint160(USDC))),
            targetChain,
            bytes32(uint256(uint160(ATTACKER))),
            targetChain,
            uint256(0)
        );
        bytes memory encodedVm = hex"1234";
        bytes32 vmHash = keccak256("nss-wormhole-mock-authorized-usdc-baseline");
        Signature[] memory signatures = new Signature[](0);
        VM memory parsed = VM({
            version: 1,
            timestamp: uint32(block.timestamp),
            nonce: 7,
            emitterChainId: sourceChain,
            emitterAddress: sourceEmitter,
            sequence: 777,
            consistencyLevel: 15,
            payload: payload,
            guardianSetIndex: 0,
            signatures: signatures,
            hash: vmHash
        });

        vm.mockCall(
            bridge.wormhole(),
            abi.encodeWithSignature("parseAndVerifyVM(bytes)", encodedVm),
            abi.encode(parsed, true, "")
        );

        vm.prank(ATTACKER);
        bridge.completeTransfer(encodedVm);

        uint256 bridgeAfter = usdc.balanceOf(WORMHOLE_TOKEN_BRIDGE);
        uint256 attackerAfter = usdc.balanceOf(ATTACKER);
        uint256 outstandingAfter = bridge.outstandingBridged(USDC);

        assertEq(bridgeBefore - bridgeAfter, amount, "authorized baseline bridge delta");
        assertEq(attackerAfter - attackerBefore, amount, "authorized baseline attacker delta");
        assertEq(outstandingBefore - outstandingAfter, amount, "authorized baseline outstanding delta");

        console2.log("WORMHOLE_VALUE_PROBE:mock_authorized_complete_transfer");
        console2.log("HARNESS_AUTH_MOCKED:1");
        console2.log("TOKEN_DELTA:%s", attackerAfter - attackerBefore);
        console2.log("BRIDGE_USDC_DELTA:%s", bridgeBefore - bridgeAfter);
        console2.log("OUTSTANDING_USDC_DELTA:%s", outstandingBefore - outstandingAfter);
        console2.log("BRIDGE_ACCOUNTING_VIOLATION:0");
    }
}
