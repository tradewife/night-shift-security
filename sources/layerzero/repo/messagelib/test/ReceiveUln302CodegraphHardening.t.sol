// SPDX-License-Identifier: UNLICENSED

pragma solidity ^0.8.0;

import { Test } from "forge-std/Test.sol";
import { BytesLib } from "solidity-bytes-utils/contracts/BytesLib.sol";

import { EndpointV2, Origin } from "@layerzerolabs/lz-evm-protocol-v2/contracts/EndpointV2.sol";
import { Packet } from "@layerzerolabs/lz-evm-protocol-v2/contracts/interfaces/ISendLib.sol";
import { PacketV1Codec } from "@layerzerolabs/lz-evm-protocol-v2/contracts/messagelib/libs/PacketV1Codec.sol";

import { ReceiveUln302 } from "../contracts/uln/uln302/ReceiveUln302.sol";
import { ReceiveUlnBase } from "../contracts/uln/ReceiveUlnBase.sol";
import { UlnConfig, SetDefaultUlnConfigParam } from "../contracts/uln/UlnBase.sol";

import { Setup } from "./util/Setup.sol";
import { PacketUtil } from "./util/Packet.sol";
import { Constant } from "./util/Constant.sol";

contract ReceiveUln302CodegraphHardeningTest is Test {
    Setup.FixtureV2 internal fixtureV2;
    ReceiveUln302 internal receiveUln302;
    EndpointV2 internal endpointV2;
    uint32 internal eid;

    function setUp() public {
        fixtureV2 = Setup.loadFixtureV2(Constant.EID_ETHEREUM);
        receiveUln302 = fixtureV2.receiveUln302;
        endpointV2 = fixtureV2.endpointV2;
        eid = fixtureV2.eid;
        Setup.wireFixtureV2WithRemote(fixtureV2, eid);
    }

    function test_commitVerificationReclaimsQuorumStorage() public {
        Packet memory packet = PacketUtil.newPacket(
            1,
            eid,
            address(this),
            eid,
            address(this),
            abi.encodePacked("message")
        );
        bytes memory encodedPacket = PacketV1Codec.encode(packet);
        bytes memory header = BytesLib.slice(encodedPacket, 0, 81);
        bytes32 payloadHash = keccak256(BytesLib.slice(encodedPacket, 81, encodedPacket.length - 81));
        bytes32 headerHash = keccak256(header);

        vm.prank(address(fixtureV2.dvn));
        receiveUln302.verify(header, payloadHash, 1);

        (bool submittedBefore, uint64 confirmationsBefore) = receiveUln302.hashLookup(
            headerHash,
            payloadHash,
            address(fixtureV2.dvn)
        );
        assertTrue(submittedBefore);
        assertEq(confirmationsBefore, 1);

        receiveUln302.commitVerification(header, payloadHash);

        (bool submittedAfter, uint64 confirmationsAfter) = receiveUln302.hashLookup(
            headerHash,
            payloadHash,
            address(fixtureV2.dvn)
        );
        assertFalse(submittedAfter);
        assertEq(confirmationsAfter, 0);

        vm.expectRevert(ReceiveUlnBase.LZ_ULN_Verifying.selector);
        receiveUln302.commitVerification(header, payloadHash);
    }

    function test_commitVerificationCannotReuseQuorumAcrossDifferentHeader() public {
        bytes32 payloadHash = keccak256("shared-payload-hash");

        Packet memory packetA = PacketUtil.newPacket(
            1,
            eid,
            address(this),
            eid,
            address(this),
            abi.encodePacked("message")
        );
        bytes memory encodedA = PacketV1Codec.encode(packetA);
        bytes memory headerA = BytesLib.slice(encodedA, 0, 81);

        Packet memory packetB = PacketUtil.newPacket(
            2,
            eid,
            address(this),
            eid,
            address(0xBEEF),
            abi.encodePacked("message")
        );
        bytes memory encodedB = PacketV1Codec.encode(packetB);
        bytes memory headerB = BytesLib.slice(encodedB, 0, 81);

        vm.prank(address(fixtureV2.dvn));
        receiveUln302.verify(headerA, payloadHash, 1);

        vm.expectRevert(ReceiveUlnBase.LZ_ULN_Verifying.selector);
        receiveUln302.commitVerification(headerB, payloadHash);
    }

    function test_stalePartialVerificationBecomesCommittableAfterDefaultConfigRelaxation() public {
        address secondDvn = address(0xBEEF);
        _setDefaultConfig(UlnConfig(1, 2, 0, 0, _pair(address(fixtureV2.dvn), secondDvn), new address[](0)));

        Packet memory packet = PacketUtil.newPacket(
            1,
            eid,
            address(this),
            eid,
            address(this),
            abi.encodePacked("message")
        );
        bytes memory encodedPacket = PacketV1Codec.encode(packet);
        bytes memory header = BytesLib.slice(encodedPacket, 0, 81);
        bytes32 payloadHash = keccak256(BytesLib.slice(encodedPacket, 81, encodedPacket.length - 81));

        vm.prank(address(fixtureV2.dvn));
        receiveUln302.verify(header, payloadHash, 1);

        vm.expectRevert(ReceiveUlnBase.LZ_ULN_Verifying.selector);
        receiveUln302.commitVerification(header, payloadHash);

        _setDefaultConfig(UlnConfig(1, 1, 0, 0, _single(address(fixtureV2.dvn)), new address[](0)));
        receiveUln302.commitVerification(header, payloadHash);
    }

    function _setDefaultConfig(UlnConfig memory config) internal {
        SetDefaultUlnConfigParam[] memory params = new SetDefaultUlnConfigParam[](1);
        params[0] = SetDefaultUlnConfigParam(eid, config);
        receiveUln302.setDefaultUlnConfigs(params);
    }

    function _single(address dvn) internal pure returns (address[] memory dvns) {
        dvns = new address[](1);
        dvns[0] = dvn;
    }

    function _pair(address dvnA, address dvnB) internal pure returns (address[] memory dvns) {
        dvns = new address[](2);
        if (dvnA < dvnB) {
            dvns[0] = dvnA;
            dvns[1] = dvnB;
        } else {
            dvns[0] = dvnB;
            dvns[1] = dvnA;
        }
    }

    function allowInitializePath(Origin calldata) external pure returns (bool) {
        return true;
    }
}
