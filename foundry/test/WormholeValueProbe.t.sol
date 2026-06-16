// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

interface IERC20Balance {
    function balanceOf(address account) external view returns (uint256);
}

interface IERC20Meta is IERC20Balance {
    function decimals() external view returns (uint8);
}

interface IWormholeTokenBridgeValueProbe {
    function completeTransfer(bytes memory encodedVm) external;
    function bridgeContracts(uint16 chainId) external view returns (bytes32);
    function chainId() external view returns (uint16);
    function createWrapped(bytes memory encodedVm) external returns (address token);
    function isTransferCompleted(bytes32 hash) external view returns (bool);
    function isWrappedAsset(address token) external view returns (bool);
    function outstandingBridged(address token) external view returns (uint256);
    function parseAssetMeta(bytes memory encoded) external pure returns (AssetMeta memory meta);
    function parseTransfer(bytes memory encoded) external pure returns (Transfer memory transfer);
    function parseTransferWithPayload(bytes memory encoded)
        external
        pure
        returns (TransferWithPayload memory transfer);
    function wormhole() external view returns (address);
    function wrappedAsset(uint16 tokenChainId, bytes32 tokenAddress) external view returns (address);
}

interface IWormholeCoreValueProbe {
    function parseAndVerifyVM(bytes calldata encodedVM)
        external
        view
        returns (VM memory vm, bool valid, string memory reason);
}

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

struct Transfer {
    uint8 payloadID;
    uint256 amount;
    bytes32 tokenAddress;
    uint16 tokenChain;
    bytes32 to;
    uint16 toChain;
    uint256 fee;
}

struct TransferWithPayload {
    uint8 payloadID;
    uint256 amount;
    bytes32 tokenAddress;
    uint16 tokenChain;
    bytes32 to;
    uint16 toChain;
    bytes32 fromAddress;
    bytes payload;
}

struct AssetMeta {
    uint8 payloadID;
    bytes32 tokenAddress;
    uint16 tokenChain;
    uint8 decimals;
    bytes32 symbol;
    bytes32 name;
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

    function _truncateAddress(bytes32 value) internal pure returns (address) {
        require(bytes12(value) == 0, "not an EVM address");
        return address(uint160(uint256(value)));
    }

    function _loadVaaOrSkip(string memory envName) internal returns (bytes memory encodedVm) {
        try vm.envBytes(envName) returns (bytes memory configured) {
            encodedVm = configured;
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

    /// @notice Optional real signed VAA replay. Set WORMHOLE_REAL_VAA_HEX to enable.
    function testForkWormholeRealSignedVaaAccountingDifferential() public {
        _forkOrSkip(ETHEREUM_RPC, vm.envOr("FORK_BLOCK_NUMBER", uint256(0)));

        bytes memory encodedVm = _loadVaaOrSkip("WORMHOLE_REAL_VAA_HEX");

        IWormholeTokenBridgeValueProbe bridge = IWormholeTokenBridgeValueProbe(WORMHOLE_TOKEN_BRIDGE);
        IWormholeCoreValueProbe core = IWormholeCoreValueProbe(bridge.wormhole());
        (VM memory parsed, bool valid, string memory reason) = core.parseAndVerifyVM(encodedVm);
        assertTrue(valid, reason);
        assertEq(bridge.bridgeContracts(parsed.emitterChainId), parsed.emitterAddress, "unregistered emitter");

        Transfer memory transfer;
        if (uint8(parsed.payload[0]) == 1) {
            transfer = bridge.parseTransfer(parsed.payload);
        } else {
            TransferWithPayload memory payload3 = bridge.parseTransferWithPayload(parsed.payload);
            transfer = Transfer({
                payloadID: payload3.payloadID,
                amount: payload3.amount,
                tokenAddress: payload3.tokenAddress,
                tokenChain: payload3.tokenChain,
                to: payload3.to,
                toChain: payload3.toChain,
                fee: 0
            });
        }
        assertEq(transfer.toChain, bridge.chainId(), "VAA does not target Ethereum token bridge");
        assertEq(transfer.tokenChain, bridge.chainId(), "probe expects native-chain release accounting");

        address token = _truncateAddress(transfer.tokenAddress);
        address recipient = _truncateAddress(transfer.to);
        IERC20Balance erc20 = IERC20Balance(token);
        uint256 bridgeBefore = erc20.balanceOf(WORMHOLE_TOKEN_BRIDGE);
        uint256 recipientBefore = erc20.balanceOf(recipient);
        uint256 outstandingBefore = bridge.outstandingBridged(token);
        bool completedBefore = bridge.isTransferCompleted(parsed.hash);

        vm.prank(ATTACKER);
        if (completedBefore) {
            vm.expectRevert();
            bridge.completeTransfer(encodedVm);
        } else {
            bridge.completeTransfer(encodedVm);
        }

        uint256 bridgeAfter = erc20.balanceOf(WORMHOLE_TOKEN_BRIDGE);
        uint256 recipientAfter = erc20.balanceOf(recipient);
        uint256 outstandingAfter = bridge.outstandingBridged(token);

        if (completedBefore) {
            assertEq(bridgeAfter, bridgeBefore, "completed VAA changed bridge balance");
            assertEq(recipientAfter, recipientBefore, "completed VAA changed recipient balance");
            assertEq(outstandingAfter, outstandingBefore, "completed VAA changed outstanding");
            console2.log("WORMHOLE_REAL_VAA_REPLAY:already_completed");
            console2.log("WORMHOLE_VALUE_PROBE:real_signed_vaa_already_completed");
            console2.log("TOKEN_DELTA:0");
            console2.log("DELTA_WEI:0");
        } else {
            uint256 nativeAmount = transfer.amount * 10 ** 10;
            assertEq(bridgeBefore - bridgeAfter, nativeAmount, "real VAA bridge delta");
            assertEq(recipientAfter - recipientBefore, nativeAmount, "real VAA recipient delta");
            assertEq(outstandingBefore - outstandingAfter, transfer.amount, "real VAA outstanding delta");
            console2.log("WORMHOLE_REAL_VAA_REPLAY:completed_on_fork");
            console2.log("WORMHOLE_VALUE_PROBE:real_signed_vaa_completed_on_fork");
            console2.log("TOKEN_DELTA:%s", recipientAfter - recipientBefore);
            console2.log("OUTSTANDING_USDC_DELTA:%s", outstandingBefore - outstandingAfter);
        }

        console2.log("REAL_SIGNED_VAA:1");
        console2.log("AUTHORIZED_REPLAY:1");
        console2.log("HARNESS_AUTH_MOCKED:0");
        console2.log("BRIDGE_ACCOUNTING_VIOLATION:0");
    }

    /// @notice Optional real wrapped-mint VAA replay. Set WORMHOLE_REAL_WRAPPED_VAA_HEX.
    function testForkWormholeRealWrappedMintAccountingDifferential() public {
        _forkOrSkip(ETHEREUM_RPC, vm.envOr("FORK_BLOCK_NUMBER", uint256(0)));

        bytes memory encodedVm = _loadVaaOrSkip("WORMHOLE_REAL_WRAPPED_VAA_HEX");
        IWormholeTokenBridgeValueProbe bridge = IWormholeTokenBridgeValueProbe(WORMHOLE_TOKEN_BRIDGE);
        IWormholeCoreValueProbe core = IWormholeCoreValueProbe(bridge.wormhole());
        (VM memory parsed, bool valid, string memory reason) = core.parseAndVerifyVM(encodedVm);
        assertTrue(valid, reason);
        assertEq(bridge.bridgeContracts(parsed.emitterChainId), parsed.emitterAddress, "unregistered emitter");

        Transfer memory transfer;
        if (uint8(parsed.payload[0]) == 1) {
            transfer = bridge.parseTransfer(parsed.payload);
        } else {
            TransferWithPayload memory payload3 = bridge.parseTransferWithPayload(parsed.payload);
            transfer = Transfer({
                payloadID: payload3.payloadID,
                amount: payload3.amount,
                tokenAddress: payload3.tokenAddress,
                tokenChain: payload3.tokenChain,
                to: payload3.to,
                toChain: payload3.toChain,
                fee: 0
            });
        }
        assertEq(transfer.toChain, bridge.chainId(), "wrapped VAA does not target Ethereum");
        assertTrue(transfer.tokenChain != bridge.chainId(), "expected foreign-token mint");

        address wrapped = bridge.wrappedAsset(transfer.tokenChain, transfer.tokenAddress);
        assertTrue(wrapped != address(0), "wrapped asset must exist before transfer replay");
        address recipient = _truncateAddress(transfer.to);
        IERC20Meta token = IERC20Meta(wrapped);
        uint256 recipientBefore = token.balanceOf(recipient);
        bool completedBefore = bridge.isTransferCompleted(parsed.hash);

        vm.prank(ATTACKER);
        if (completedBefore) {
            vm.expectRevert();
            bridge.completeTransfer(encodedVm);
        } else {
            bridge.completeTransfer(encodedVm);
        }

        uint256 recipientAfter = token.balanceOf(recipient);
        if (completedBefore) {
            assertEq(recipientAfter, recipientBefore, "completed wrapped VAA changed recipient balance");
            console2.log("WORMHOLE_WRAPPED_VAA_REPLAY:already_completed");
            console2.log("TOKEN_DELTA:0");
            console2.log("DELTA_WEI:0");
        } else {
            uint256 nativeAmount = transfer.amount * 10 ** (uint256(token.decimals()) > 8 ? token.decimals() - 8 : 0);
            assertEq(recipientAfter - recipientBefore, nativeAmount, "real wrapped VAA recipient delta");
            console2.log("WORMHOLE_WRAPPED_VAA_REPLAY:completed_on_fork");
            console2.log("TOKEN_DELTA:%s", recipientAfter - recipientBefore);
        }

        console2.log("REAL_SIGNED_VAA:1");
        console2.log("AUTHORIZED_REPLAY:1");
        console2.log("HARNESS_AUTH_MOCKED:0");
        console2.log("BRIDGE_ACCOUNTING_VIOLATION:0");
    }

    /// @notice Optional real asset-meta replay. Set WORMHOLE_REAL_ASSET_META_VAA_HEX.
    function testForkWormholeRealAssetMetaCreateWrappedDifferential() public {
        _forkOrSkip(ETHEREUM_RPC, vm.envOr("FORK_BLOCK_NUMBER", uint256(0)));

        bytes memory encodedVm = _loadVaaOrSkip("WORMHOLE_REAL_ASSET_META_VAA_HEX");
        IWormholeTokenBridgeValueProbe bridge = IWormholeTokenBridgeValueProbe(WORMHOLE_TOKEN_BRIDGE);
        IWormholeCoreValueProbe core = IWormholeCoreValueProbe(bridge.wormhole());
        (VM memory parsed, bool valid, string memory reason) = core.parseAndVerifyVM(encodedVm);
        assertTrue(valid, reason);

        AssetMeta memory meta = bridge.parseAssetMeta(parsed.payload);
        if (meta.tokenChain == bridge.chainId()) {
            console2.log("WORMHOLE_ASSET_META_REPLAY:same_chain_metadata");
            vm.skip(true);
        }
        assertEq(bridge.bridgeContracts(parsed.emitterChainId), parsed.emitterAddress, "unregistered emitter");
        address wrappedBefore = bridge.wrappedAsset(meta.tokenChain, meta.tokenAddress);

        if (wrappedBefore != address(0)) {
            vm.expectRevert();
            bridge.createWrapped(encodedVm);
            assertEq(bridge.wrappedAsset(meta.tokenChain, meta.tokenAddress), wrappedBefore);
            console2.log("WORMHOLE_ASSET_META_REPLAY:already_wrapped");
        } else {
            address created = bridge.createWrapped(encodedVm);
            assertTrue(created != address(0), "createWrapped returned zero");
            assertEq(bridge.wrappedAsset(meta.tokenChain, meta.tokenAddress), created);
            assertTrue(bridge.isWrappedAsset(created), "created wrapper not registered");
            console2.log("WORMHOLE_ASSET_META_REPLAY:created_on_fork");
        }

        console2.log("REAL_SIGNED_VAA:1");
        console2.log("AUTHORIZED_REPLAY:1");
        console2.log("HARNESS_AUTH_MOCKED:0");
        console2.log("BRIDGE_ACCOUNTING_VIOLATION:0");
        console2.log("TOKEN_DELTA:0");
    }
}
