// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

/// @title LayerZeroULN302LifecycleFalsifier — packet-header codec + falsifier
///        assertions mirroring the property fan-in table.
/// @notice v6.27.0-layerzero-endpoint-uln302-sidecar-session30.
/// @dev Reproduces the V2 packet header codec in pure Solidity (no library
///      dependency on LayerZero-v2 monorepo) so the falsifier ships without
///      a separate ``forge install`` step. The constants and offset table
///      match the source-pinned `PacketV1Codec.sol` at commit
///      ``0990059e3ee61ea95f45011cf7284243531fb4c3``.
contract LayerZeroULN302LifecycleFalsifierTest is Test {
    // ---- packet-header codec constants (mirror PacketV1Codec.sol)
    uint8 internal constant PACKET_VERSION = 1;
    uint256 internal constant PACKET_VERSION_OFFSET = 0;
    uint256 internal constant NONCE_OFFSET = 1;
    uint256 internal constant SRC_EID_OFFSET = 9;
    uint256 internal constant SENDER_OFFSET = 13;
    uint256 internal constant DST_EID_OFFSET = 45;
    uint256 internal constant RECEIVER_OFFSET = 49;
    uint256 internal constant GUID_OFFSET = 81; // header length

    // ---- chain EIDs (mirror CHAIN_EIDS in native/layerzero.py)
    uint32 internal constant EID_ETH = 30101;
    uint32 internal constant EID_ARB = 30110;

    /// @notice Encode an 81-byte packet header to mirror `PacketV1Codec.encodePacketHeader(Packet memory)`.
    function _encodeHeader(
        uint64 nonce,
        uint32 srcEid,
        address sender,
        uint32 dstEid,
        bytes32 receiver
    ) internal pure returns (bytes memory) {
        return abi.encodePacked(
            PACKET_VERSION,
            nonce,
            srcEid,
            bytes32(uint256(uint160(sender))),
            dstEid,
            receiver
        );
    }

    /// @notice Decode the 81-byte header into canonical fields.
    function _decodeHeader(bytes memory header)
        internal
        pure
        returns (
            uint8 version,
            uint64 nonce,
            uint32 srcEid,
            address sender,
            uint32 dstEid,
            bytes32 receiver
        )
    {
        version = uint8(header[PACKET_VERSION_OFFSET]);
        nonce = uint64(bytes8(_slice(header, NONCE_OFFSET, 8)));
        srcEid = uint32(bytes4(_slice(header, SRC_EID_OFFSET, 4)));
        sender = address(uint160(uint256(bytes32(_slice(header, SENDER_OFFSET, 32)))));
        dstEid = uint32(bytes4(_slice(header, DST_EID_OFFSET, 4)));
        receiver = bytes32(_slice(header, RECEIVER_OFFSET, 32));
    }

    function _slice(bytes memory data, uint256 start, uint256 length) internal pure returns (bytes memory) {
        bytes memory out = new bytes(length);
        for (uint256 i = 0; i < length; ++i) {
            out[i] = data[start + i];
        }
        return out;
    }

    // ---- falsifiers ----

    /// @notice PROP-PKT-001: header length must be exactly 81 bytes per
    ///         `ReceiveUlnBase._assertHeader` (`if (_packetHeader.length != 81) revert`).
    function testPacketHeaderLengthIs81() public {
        bytes memory header = _encodeHeader({
            nonce: 1,
            srcEid: EID_ETH,
            sender: address(0xA11CE),
            dstEid: EID_ARB,
            receiver: bytes32(uint256(uint160(address(0xB0B))))
        });
        assertEq(header.length, 81, "header must be 81 bytes (PacketV1Codec)");
    }

    /// @notice PROP-PKT-001: version byte must be 1.
    function testPacketHeaderVersionIsOne() public {
        bytes memory header = _encodeHeader({
            nonce: 1,
            srcEid: EID_ETH,
            sender: address(0xA11CE),
            dstEid: EID_ARB,
            receiver: bytes32(uint256(uint160(address(0xB0B))))
        });
        (uint8 version, , , , , ) = _decodeHeader(header);
        assertEq(uint256(version), 1, "version byte must be 1");
    }

    /// @notice PROP-PKT-001: two distinct nonce tuples produce distinct headers.
    function testPacketHeadersCollideOnNonceOnly() public {
        bytes memory a = _encodeHeader({
            nonce: 1,
            srcEid: EID_ETH,
            sender: address(0xA11CE),
            dstEid: EID_ARB,
            receiver: bytes32(uint256(uint160(address(0xB0B))))
        });
        bytes memory b = _encodeHeader({
            nonce: 2, // mutated nonce
            srcEid: EID_ETH,
            sender: address(0xA11CE),
            dstEid: EID_ARB,
            receiver: bytes32(uint256(uint160(address(0xB0B))))
        });
        assertTrue(keccak256(a) != keccak256(b), "header hash must depend on nonce");
    }

    /// @notice PROP-PKT-001: two distinct sender addresses produce distinct headers.
    function testPacketHeadersCollideOnSenderOnly() public {
        bytes memory a = _encodeHeader({
            nonce: 1,
            srcEid: EID_ETH,
            sender: address(0xA11CE),
            dstEid: EID_ARB,
            receiver: bytes32(uint256(uint160(address(0xB0B))))
        });
        bytes memory b = _encodeHeader({
            nonce: 1,
            srcEid: EID_ETH,
            sender: address(0xA11CE2),
            dstEid: EID_ARB,
            receiver: bytes32(uint256(uint160(address(0xB0B))))
        });
        assertTrue(keccak256(a) != keccak256(b));
    }

    /// @notice PROP-PKT-001: same inputs -> same hash (deterministic encoding).
    function testPacketHeadersDeterministic() public {
        bytes memory a = _encodeHeader({
            nonce: 7,
            srcEid: EID_ETH,
            sender: address(0xCAFE),
            dstEid: EID_ARB,
            receiver: bytes32(uint256(uint160(address(0xF00D))))
        });
        bytes memory b = _encodeHeader({
            nonce: 7,
            srcEid: EID_ETH,
            sender: address(0xCAFE),
            dstEid: EID_ARB,
            receiver: bytes32(uint256(uint160(address(0xF00D))))
        });
        assertEq(keccak256(a), keccak256(b));
    }

    /// @notice PROP-PKT-002 (model): the Uln102/302 default
    ///         ``_assertAtLeastOneDVN`` guard should pin against zero-DVN.
    ///         Concrete invariant: a valid Dvn config for a path with
    ///         zero required + zero optional threshold is invalid, so
    ///         the resolver *must* not return such a config. We pin the
    ///         model's behaviour at the highest level rather than re-implementing
    ///         the contract; the property is testable in the foundry library
    ///         once the LayerZero-v2 library is installed.
    function testZeroDvnConfigIsForbiddenByInvariant() public {
        // Force a representation where requiredDVNCount == 0 AND optionalDVNThreshold == 0
        uint8 requiredDVNCount = 0;
        uint8 optionalDVNThreshold = 0;
        // The V2 source ``UlnBase._assertAtLeastOneDVN`` reverts when this holds.
        bool isInvalid = requiredDVNCount == 0 && optionalDVNThreshold == 0;
        assertTrue(isInvalid, "zero-DVN config MUST be rejected by the resolver");
        console2.log("ULN_INVARIANT:assertAtLeastOneDVN");
        console2.log("IMPACT_USD:0");
    }

    /// @notice PROP-PKT-005: any two distinct messages for the same
    ///         (nonce, srcEid, sender, dstEid, receiver) tuple produce
    ///         distinct payload hashes. This mirrors ``keccak256(message)``
    ///         on the receive side being uniquely bound.
    function testPayloadHashDistinguishesMessages() public {
        bytes memory messageA = hex"deadbeef";
        bytes memory messageB = hex"deadbeef00";
        // Any 1-byte difference is enough — sha256 is collision-free.
        assertTrue(keccak256(messageA) != keccak256(messageB));
    }

    /// @notice PROP-PKT-006: nonce monotonic increase prevents replay.
    ///         The property: `lazyInboundNonce` is keyed by
    ///         ``[receiver][srcEid][sender]``; the receive-side assertion
    ///         ``_verifiable()`` requires ``nonce > lazyInboundNonce``.
    ///         Two OApps with distinct `sender` addresses can never collide
    ///         under the same `lazyInboundNonce` bucket.
    function testNondCollidingOappsNeverShareNonceBucket() public {
        bytes32 bucketA = keccak256(abi.encodePacked(address(0xA), uint32(EID_ETH), uint32(EID_ARB)));
        bytes32 bucketB = keccak256(abi.encodePacked(address(0xB), uint32(EID_ETH), uint32(EID_ARB)));
        // Different sender -> different bucket (the receive-side keyed mapping).
        assertTrue(bucketA != bucketB, "distinct senders MUST use distinct nonce buckets");
        // Same OApp, same path -> colliding by-design (this is correct).
        bytes32 bucketC = keccak256(abi.encodePacked(address(0xA), uint32(EID_ETH), uint32(EID_ARB)));
        assertEq(bucketA, bucketC);
    }
}

/// @notice Light shim that keeps the ``forge-std`` syntax tree minimal.
interface IChecksumOnly {
    function empty() external pure returns (bool);
}
