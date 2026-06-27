// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

struct HarnessMessagingParams {
    uint32 dstEid;
    bytes32 receiver;
    bytes message;
    bytes options;
    bool payInLzToken;
}

struct HarnessMessagingFee {
    uint256 nativeFee;
    uint256 lzTokenFee;
}

interface IEndpointV2Quote {
    function quote(
        HarnessMessagingParams calldata _params,
        address _sender
    ) external view returns (HarnessMessagingFee memory);
}

interface IEndpointV2Support {
    function isSupportedEid(uint32 _eid) external view returns (bool);
}

/// @title LayerZeroEndpointHarness — fork-mode smoke tests for the V2 EndpointV2.
/// @notice v6.27.0-layerzero-endpoint-uln302-sidecar-session30.
/// @dev The LayerZero V2 contracts are not part of the repo's library layout
///      (the upstream is an npm monorepo). This harness operates against a
///      pinned RPC fork and uses *interface-only* assertions + raw bytecode
///      size checks. Concrete ABI-driven calls are reserved for the
///      matching ULN lifecycle harness once the optional
///      ``foundry/lib/layerzero-v2`` library is installed by Phase 1 close.
/// @dev All tests honor the ``ETHEREUM_RPC_URL`` env; absence triggers a
///      ``skip(true)`` so CI defaults to green even without network.
contract LayerZeroEndpointHarnessTest is Test {
    string constant ETHEREUM_RPC = "ETHEREUM_RPC_URL";

    // LayerZero V2 addresses — same deterministic CREATE2-style deploy across chains.
    // Solidity 0.8.24 enforces EIP-55 checksum on 20-byte hex literals even with
    // an explicit `uint160` cast. Workaround: split the 20-byte address into
    // two pieces that each fit in a uint128 (high 16 bytes / low 4 bytes)
    // and assemble via `(hi << 32) | lo`. Bitwise identical to:
    //   - 0x1a44076050125825900e736c501f859c50fe728c  (EndpointV2)
    //   - 0xbb2ea70c9e858123480642cf96acbcce1372dce1  (SendUln302)
    //   - 0xc02ab410f0734efa3f14628780e6e695156024c2  (ReceiveUln302)
    address constant ENDPOINT_V2 = address(uint160(
        (uint256(uint128(0x1a44076050125825900e736c501f859c)) << 32)
        | uint256(uint128(0x50fe728c))
    ));
    address constant SEND_ULN_302 = address(uint160(
        (uint256(uint128(0xbb2ea70c9e858123480642cf96acbcce)) << 32)
        | uint256(uint128(0x1372dce1))
    ));
    address constant RECEIVE_ULN_302 = address(uint160(
        (uint256(uint128(0xc02ab410f0734efa3f14628780e6e695)) << 32)
        | uint256(uint128(0x156024c2))
    ));
    uint32 constant WORKING_EID = 30110;
    uint32 constant TAC_EID = 30155;

    function _forkOrSkip(string memory rpcEnv) internal {
        try vm.envString(rpcEnv) returns (string memory rpc) {
            vm.createSelectFork(rpc);
        } catch {
            vm.skip(true);
        }
    }

    /// @notice Smoke test — bytecode-only sanity check that the deployed
    ///         EndpointV2 is non-trivial on Ethereum mainnet.
    ///         Phase-1 acceptance gate per spec §0 v6.27 acceptance list:
    ///         "All Foundry harnesses compile clean (``forge build`` exit 0);
    ///          `forge test --match-path test/LayerZero*.t.sol` runs and
    ///          emits measured deltas; honest-zero runs print IMPACT_USD:0."
    function testForkEndpointV2BytecodeSizeNonZero() public {
        _forkOrSkip(ETHEREUM_RPC);
        assertEq(block.chainid, 1, "fork must be Ethereum mainnet");

        uint256 size = ENDPOINT_V2.code.length;
        assertGt(size, 0, "EndpointV2 not deployed");
        console2.log("FORK_BLOCK:%s", block.number);
        console2.log("ENDPOINT_V2_CODE_SIZE:%s", size);
        console2.log("IMPACT_USD:0"); // honest-zero candidate
    }

    /// @notice Same bytecode sanity check for SendULN302.
    function testForkSendUln302BytecodeSizeNonZero() public {
        _forkOrSkip(ETHEREUM_RPC);
        assertEq(block.chainid, 1);

        uint256 size = SEND_ULN_302.code.length;
        assertGt(size, 0, "SendULN302 not deployed");
        console2.log("SEND_ULN_302_CODE_SIZE:%s", size);
        console2.log("IMPACT_USD:0");
    }

    /// @notice Same bytecode sanity check for ReceiveULN302.
    function testForkReceiveUln302BytecodeSizeNonZero() public {
        _forkOrSkip(ETHEREUM_RPC);
        assertEq(block.chainid, 1);

        uint256 size = RECEIVE_ULN_302.code.length;
        assertGt(size, 0, "ReceiveULN302 not deployed");
        console2.log("RECEIVE_ULN_302_CODE_SIZE:%s", size);
        console2.log("IMPACT_USD:0");
    }

    function testForkQuoteOnWorkingDefaultPathSucceeds() public {
        _forkOrSkip(ETHEREUM_RPC);
        assertEq(block.chainid, 1);
        assertTrue(IEndpointV2Support(ENDPOINT_V2).isSupportedEid(WORKING_EID), "working eid must be supported");

        HarnessMessagingFee memory fee = IEndpointV2Quote(ENDPOINT_V2).quote(_quoteParams(WORKING_EID), address(this));
        assertGt(fee.nativeFee, 0, "expected non-zero native fee");
        assertEq(fee.lzTokenFee, 0, "expected zero lz token fee");
    }

    function testForkQuoteOnTacDefaultPathReverts() public {
        _forkOrSkip(ETHEREUM_RPC);
        assertEq(block.chainid, 1);
        assertTrue(IEndpointV2Support(ENDPOINT_V2).isSupportedEid(TAC_EID), "tac eid must be supported");

        vm.expectRevert();
        IEndpointV2Quote(ENDPOINT_V2).quote(_quoteParams(TAC_EID), address(this));
    }

    /// @notice Selector sanity — independent keccak recomputation.
    ///         Mirrors `tests/test_native_layerzero.py:test_feature_selectors_match_first_four_bytes_keccak`.
    function testEndpointV2SendSelector() public {
        bytes4 expectedSend = bytes4(keccak256("send((uint32,bytes32,bytes,bytes,bool),address)"));
        bytes4 expectedVerify = bytes4(keccak256("verify((uint32,bytes32,uint64),address,bytes32)"));
        bytes4 expectedLzReceive = bytes4(keccak256("lzReceive((uint32,bytes32,uint64),address,bytes32,bytes,bytes)"));
        bytes4 expectedQuote = bytes4(keccak256("quote((uint32,bytes32,bytes,bytes,bool),address)"));

        // Pin canonical selectors (recomputed via night_shift_security.crypto.keccak256):
        //   send   : 0x2637a450
        //   verify : 0xa825d747
        //   lzRec  : 0x0c0c389e
        //   quote  : 0xddc28c58
        assertEq(expectedSend,    bytes4(0x2637a450));
        assertEq(expectedVerify,  bytes4(0xa825d747));
        assertEq(expectedLzReceive, bytes4(0x0c0c389e));
        assertEq(expectedQuote,   bytes4(0xddc28c58));

        console2.log("ENDPOINT_V2_SELECTOR_SEND:0x2637a450");
        console2.log("ENDPOINT_V2_SELECTOR_VERIFY:0xa825d747");
        console2.log("ENDPOINT_V2_SELECTOR_LZRECEIVE:0x0c0c389e");
        console2.log("ENDPOINT_V2_SELECTOR_QUOTE:0xddc28c58");
        console2.log("IMPACT_USD:0");
    }

    /// @notice Send-side Uln base selector sanity check.
    function testReceiveUln302CommitVerificationSelector() public {
        bytes4 expectedCommit = bytes4(keccak256("commitVerification(bytes,bytes32)"));
        bytes4 expectedVerify = bytes4(keccak256("verify(bytes,bytes32,uint64)"));

        // Pin canonical selectors for ReceiveUln302 (DVN-controlled functions).
        //   commitVerification : 0x0894edf1
        //   verify             : 0x0223536e
        // Source: signature -> keccak256 == first 4 bytes.
        assertEq(expectedCommit, bytes4(0x0894edf1));
        assertEq(expectedVerify, bytes4(0x0223536e));

        console2.log("RECV_COMMIT_VERIFY_SELECTOR:0x0894edf1");
        console2.log("RECV_VERIFY_SELECTOR:0x0223536e");
        console2.log("IMPACT_USD:0");
    }

    function _quoteParams(uint32 dstEid) internal view returns (HarnessMessagingParams memory params) {
        params = HarnessMessagingParams({
            dstEid: dstEid,
            receiver: bytes32(uint256(uint160(address(this)))),
            message: bytes("night-shift"),
            options: _lzReceiveOptions(200000),
            payInLzToken: false
        });
    }

    function _lzReceiveOptions(uint128 gasLimit) internal pure returns (bytes memory) {
        return abi.encodePacked(uint16(3), uint8(1), uint16(17), uint8(1), gasLimit);
    }
}
