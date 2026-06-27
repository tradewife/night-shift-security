// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test, console2 } from "forge-std/Test.sol";

struct AuditMessagingParams {
    uint32 dstEid;
    bytes32 receiver;
    bytes message;
    bytes options;
    bool payInLzToken;
}

struct AuditMessagingFee {
    uint256 nativeFee;
    uint256 lzTokenFee;
}

struct AuditOrigin {
    uint32 srcEid;
    bytes32 sender;
    uint64 nonce;
}

interface IAuditEndpoint {
    function isSupportedEid(uint32 _eid) external view returns (bool);

    function defaultReceiveLibrary(uint32 _eid) external view returns (address);

    function defaultReceiveLibraryTimeout(uint32 _eid) external view returns (address lib, uint256 expiry);

    function getReceiveLibrary(
        address _receiver,
        uint32 _srcEid
    ) external view returns (address lib, bool isDefault);

    function isValidReceiveLibrary(
        address _receiver,
        uint32 _srcEid,
        address _actualReceiveLib
    ) external view returns (bool);

    function quote(
        AuditMessagingParams calldata _params,
        address _sender
    ) external view returns (AuditMessagingFee memory);

    function verify(
        AuditOrigin calldata _origin,
        address _receiver,
        bytes32 _payloadHash
    ) external;
}

interface IAuditReceiveLib {
    function messageLibType() external view returns (uint8);

    function version() external view returns (uint64 major, uint8 minor, uint8 endpointVersion);

    function getConfig(uint32 _eid, address _oapp, uint32 _configType) external view returns (bytes memory);
}

/// @title LayerZeroEndpointIsSupportedEidAudit — Direction C fork PoC.
/// @notice Demonstrates the live contradiction between `EndpointV2.isSupportedEid`
///         returning `true` for several EIDs and the corresponding default
///         receive-library path being permanently unusable for verification.
///
/// @dev Anchors the v6.28 codegraph-hardening session31 trail. Strictly read-only
///      against an Ethereum mainnet fork. Honors `ETHEREUM_RPC_URL` and defaults
///      to `skip(true)` when absent. Local-only footprint.
contract LayerZeroEndpointIsSupportedEidAuditTest is Test {
    string constant ETHEREUM_RPC = "ETHEREUM_RPC_URL";
    // LayerZero V2 addresses — checksum-correct from Alchemy-backed live reads on 2026-06-27.
    address constant ENDPOINT_V2 = 0x1a44076050125825900e736c501f859c50fE728c;
    address constant RECEIVE_LIB_302 = 0xc02Ab410f0734EFa3F14628780e6e695156024C2;
    address constant DEAD_DVN = 0x000000000000000000000000000000000000dEaD;

    // Curated EIDs taken from the live Alchemy-backed scan on 2026-06-27:
    // - 30155 (Tac)        : live default sole required DVN == 0x...dEaD
    // - 30301 (Read chan)  : live default sole required DVN == 0x...dEaD
    // - 30309 (Read chan)  : sampled with the same DVN shape
    // - 30110 (Arbitrum)   : POSITIVE control; has working DVNs and a normal quote
    // - 30202 (HyperEVM)   : reported support but default path is broken under docs
    uint32[] internal AUDIT_EIDS = [30155, 30301, 30309, 30110, 30202];

    event AuditProbe(
        uint32 eid,
        bool supportedFlag,
        bool defaultQuoteReverts,
        bool deadDvnAtCodeSize
    );

    function _forkOrSkip(string memory rpcEnv) internal {
        try vm.envString(rpcEnv) returns (string memory rpc) {
            vm.createSelectFork(rpc);
        } catch {
            vm.skip(true);
        }
    }

    function testForkDeadDvnAuditWaitsForDefaultReadiness() public {
        _forkOrSkip(ETHEREUM_RPC);
        assertEq(block.chainid, 1, "fork must be Ethereum mainnet");

        uint256 deadDvnAtCodeSize = DEAD_DVN.code.length;
        assertEq(deadDvnAtCodeSize, 0, "0x...dEaD must remain a dead address");

        IAuditEndpoint endpoint = IAuditEndpoint(ENDPOINT_V2);
        bytes memory options = abi.encodePacked(uint16(3), uint8(1), uint16(17), uint8(1), uint128(200_000));
        bytes32 receiver = bytes32(uint256(uint160(address(this))));

        uint256[3] memory counters;
        for (uint256 i = 0; i < AUDIT_EIDS.length; ++i) {
            uint32 eid = AUDIT_EIDS[i];
            counters = _auditSingleEid(endpoint, eid, receiver, options, counters);
        }
        uint256 supportedTrueCount = counters[0];
        uint256 deadDvnEidCount = counters[1];
        uint256 quoteRevertingEidCount = counters[2];

        console2.log("EID_SCAN_COUNT %d", AUDIT_EIDS.length);
        console2.log("EID_SUPPORTED_TRUE %d", supportedTrueCount);
        console2.log("EID_CONTRADICTION_FOUND %d", deadDvnEidCount);
        console2.log("EID_QUOTE_REVERT_FOUND %d", quoteRevertingEidCount);
        console2.log("IMPACT_EID_COUNT %d", deadDvnEidCount);
        console2.log("VERTEX_NOTES_DEAD_DEFAULT_LIB %d", deadDvnEidCount);
        console2.log("IMPACT_USD 0");
        console2.log("SUBMIT_READY 0");
    }

    function _auditSingleEid(
        IAuditEndpoint endpoint,
        uint32 eid,
        bytes32 receiver,
        bytes memory options,
        uint256[3] memory counters
    )
        internal
        returns (uint256[3] memory)
    {
        bool isSupported = endpoint.isSupportedEid(eid);
        address defaultLib = endpoint.defaultReceiveLibrary(eid);
        (address timeoutLib, ) = endpoint.defaultReceiveLibraryTimeout(eid);
        // Use the real default; fall back to the timeout-paired lib if the
        // default itself is zero (some EIDs only set the timeout version).
        address effectiveLib = defaultLib != address(0) ? defaultLib : timeoutLib;
        uint256 defaultLibCodeSize = effectiveLib.code.length;
        address firstDvn = _defaultUlnDvn(RECEIVE_LIB_302, eid, effectiveLib);
        bool contradiction = isSupported && (defaultLibCodeSize == 0 || firstDvn == DEAD_DVN);

        bool quoteReverts;
        {
            AuditMessagingParams memory params;
            params.dstEid = eid;
            params.receiver = receiver;
            params.message = bytes("dead-dvn-probe");
            params.options = options;
            params.payInLzToken = false;
            try endpoint.quote(params, address(this)) returns (AuditMessagingFee memory) {
                quoteReverts = false;
            } catch {
                quoteReverts = true;
            }
        }

        if (isSupported) counters[0] += 1;
        if (contradiction) counters[1] += 1;
        if (quoteReverts) counters[2] += 1;

        emit AuditProbe(eid, isSupported, quoteReverts, contradiction);
        _logProbe(eid, isSupported, quoteReverts, contradiction, defaultLibCodeSize, firstDvn == DEAD_DVN);

        return counters;
    }

    function _logProbe(
        uint32 eid,
        bool isSupported,
        bool quoteReverts,
        bool contradiction,
        uint256 defaultLibCodeSize,
        bool deadDvnInConfig
    ) internal {
        console2.log("EID_PROBE %d", eid);
        console2.log("PROBE_SUPPORTED %s", isSupported);
        console2.log("PROBE_QUOTE_REVERTS %s", quoteReverts);
        console2.log("PROBE_CONTRADICTION %s", contradiction);
        console2.log("PROBE_LIB_CODE %d", defaultLibCodeSize);
        console2.log("PROBE_DEAD_DVN_IN_CONFIG %s", deadDvnInConfig);
    }

    function _defaultUlnDvn(
        address libAddr,
        uint32 eid,
        address defaultLib
    ) internal view returns (address firstRequiredDvn) {
        if (defaultLib != libAddr) return address(0);
        IAuditReceiveLib lib = IAuditReceiveLib(libAddr);
        (uint64 major, uint8 minor, uint8 endpointField) = lib.version();
        major; minor; endpointField;
        // getConfig returns abi.encode(UlnConfig). We scan the raw bytes for
        // the DEAD_DVN address (32-byte ABI-encoded word) to detect the dead
        // DVN in either requiredDVNs or optionalDVNs arrays.
        bytes memory configBytes = lib.getConfig(eid, address(0), uint32(2));
        bytes32 deadPattern = bytes32(uint256(uint160(DEAD_DVN)));
        for (uint256 i = 0; i + 32 <= configBytes.length; i += 32) {
            bytes32 word;
            assembly {
                word := mload(add(configBytes, add(i, 32)))
            }
            if (word == deadPattern) {
                return DEAD_DVN;
            }
        }
        return address(0);
    }
}
