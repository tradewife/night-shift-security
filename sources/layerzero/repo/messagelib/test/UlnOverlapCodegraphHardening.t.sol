// SPDX-License-Identifier: UNLICENSED

pragma solidity ^0.8.0;

import { Test } from "forge-std/Test.sol";
import { BytesLib } from "solidity-bytes-utils/contracts/BytesLib.sol";

import { Packet } from "@layerzerolabs/lz-evm-protocol-v2/contracts/interfaces/ISendLib.sol";
import { PacketV1Codec } from "@layerzerolabs/lz-evm-protocol-v2/contracts/messagelib/libs/PacketV1Codec.sol";
import { Origin } from "@layerzerolabs/lz-evm-protocol-v2/contracts/interfaces/ILayerZeroEndpointV2.sol";

import { SendUlnBase } from "../contracts/uln/SendUlnBase.sol";
import { ReceiveUln302 } from "../contracts/uln/uln302/ReceiveUln302.sol";
import { ReceiveUlnBase } from "../contracts/uln/ReceiveUlnBase.sol";
import { ILayerZeroDVN } from "../contracts/uln/interfaces/ILayerZeroDVN.sol";
import { UlnConfig, SetDefaultUlnConfigParam } from "../contracts/uln/UlnBase.sol";

import { Setup } from "./util/Setup.sol";
import { PacketUtil } from "./util/Packet.sol";
import { Constant } from "./util/Constant.sol";

contract SendUlnOverlapCodegraphHardeningTest is Test, SendUlnBase {
    address internal dvn = address(0x11);
    mapping(address => uint256) internal fees;

    function test_overlapChargesSameDvnTwice() public {
        UlnConfig memory config = UlnConfig(1, 1, 1, 1, _single(dvn), _single(dvn));
        ILayerZeroDVN.AssignJobParam memory param = ILayerZeroDVN.AssignJobParam(
            1,
            bytes("packetHeader"),
            bytes32(uint256(0x1234)),
            1,
            address(this)
        );

        vm.mockCall(dvn, abi.encodeWithSelector(ILayerZeroDVN.assignJob.selector), abi.encode(100));

        (uint256 totalFee, uint256[] memory dvnFees) = _assignJobs(fees, config, param, "");
        assertEq(totalFee, 200);
        assertEq(dvnFees.length, 2);
        assertEq(dvnFees[0], 100);
        assertEq(dvnFees[1], 100);
        assertEq(fees[dvn], 200);
    }

    function _single(address value) internal pure returns (address[] memory values) {
        values = new address[](1);
        values[0] = value;
    }
}

contract ReceiveUlnOverlapCodegraphHardeningTest is Test {
    Setup.FixtureV2 internal fixtureV2;
    ReceiveUln302 internal receiveUln302;
    uint32 internal eid;
    address internal optionalOnlyDvn = address(0xBEEF);

    function setUp() public {
        fixtureV2 = Setup.loadFixtureV2(Constant.EID_ETHEREUM);
        receiveUln302 = fixtureV2.receiveUln302;
        eid = fixtureV2.eid;
        Setup.wireFixtureV2WithRemote(fixtureV2, eid);
    }

    function test_singleVerificationFailsForDisjointButPassesForOverlap() public {
        _setDefaultConfig(UlnConfig(1, 1, 1, 1, _single(address(fixtureV2.dvn)), _single(optionalOnlyDvn)));
        (bytes memory headerA, bytes32 payloadHashA) = _packet(1);

        vm.prank(address(fixtureV2.dvn));
        receiveUln302.verify(headerA, payloadHashA, 1);
        vm.expectRevert(ReceiveUlnBase.LZ_ULN_Verifying.selector);
        receiveUln302.commitVerification(headerA, payloadHashA);

        _setDefaultConfig(UlnConfig(1, 1, 1, 1, _single(address(fixtureV2.dvn)), _single(address(fixtureV2.dvn))));
        (bytes memory headerB, bytes32 payloadHashB) = _packet(2);

        vm.prank(address(fixtureV2.dvn));
        receiveUln302.verify(headerB, payloadHashB, 1);
        receiveUln302.commitVerification(headerB, payloadHashB);
    }

    function _setDefaultConfig(UlnConfig memory config) internal {
        SetDefaultUlnConfigParam[] memory params = new SetDefaultUlnConfigParam[](1);
        params[0] = SetDefaultUlnConfigParam(eid, config);
        receiveUln302.setDefaultUlnConfigs(params);
    }

    function _packet(uint64 nonce) internal view returns (bytes memory header, bytes32 payloadHash) {
        Packet memory packet = PacketUtil.newPacket(
            nonce,
            eid,
            address(this),
            eid,
            address(this),
            abi.encodePacked("message")
        );
        bytes memory encodedPacket = PacketV1Codec.encode(packet);
        header = BytesLib.slice(encodedPacket, 0, 81);
        payloadHash = keccak256(BytesLib.slice(encodedPacket, 81, encodedPacket.length - 81));
    }

    function _single(address value) internal pure returns (address[] memory values) {
        values = new address[](1);
        values[0] = value;
    }

    function allowInitializePath(Origin calldata) external pure returns (bool) {
        return true;
    }
}
