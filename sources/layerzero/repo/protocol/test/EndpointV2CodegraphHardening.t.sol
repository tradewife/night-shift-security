// SPDX-License-Identifier: UNLICENSED

pragma solidity ^0.8.0;

import { AddressCast } from "../contracts/libs/AddressCast.sol";
import { Errors } from "../contracts/libs/Errors.sol";
import { Origin } from "../contracts/interfaces/ILayerZeroEndpointV2.sol";
import { SimpleMessageLib } from "../contracts/messagelib/SimpleMessageLib.sol";

import { LayerZeroTest } from "./utils/LayerZeroTest.sol";
import { OAppMock } from "./mocks/AppMock.sol";

contract EndpointV2CodegraphHardeningTest is LayerZeroTest {
    OAppMock internal oapp;
    address internal receiver;
    bytes32 internal senderB32;
    bytes32 internal payloadHash;

    function setUp() public override {
        super.setUp();
        oapp = new OAppMock(address(endpoint));
        receiver = address(oapp);
        senderB32 = AddressCast.toBytes32(address(this));
        payloadHash = keccak256(abi.encodePacked(keccak256("guid"), bytes("foo")));
    }

    function test_verifyRespectsDefaultReceiveLibraryGraceBoundary() public {
        SimpleMessageLib newMsgLib = setupSimpleMessageLib(address(endpoint), remoteEid, false);

        vm.roll(10);
        endpoint.setDefaultReceiveLibrary(remoteEid, address(newMsgLib), 5);

        vm.roll(14);
        vm.prank(address(simpleMsgLib));
        endpoint.verify(Origin(remoteEid, senderB32, 1), receiver, payloadHash);
        assertEq(endpoint.inboundPayloadHash(receiver, remoteEid, senderB32, 1), payloadHash);

        vm.roll(15);
        vm.prank(address(simpleMsgLib));
        vm.expectRevert(Errors.LZ_InvalidReceiveLibrary.selector);
        endpoint.verify(Origin(remoteEid, senderB32, 2), receiver, payloadHash);

        vm.prank(address(newMsgLib));
        endpoint.verify(Origin(remoteEid, senderB32, 2), receiver, payloadHash);
        assertEq(endpoint.inboundPayloadHash(receiver, remoteEid, senderB32, 2), payloadHash);
    }

    function test_verifyRespectsCustomReceiveLibraryTimeoutBoundary() public {
        SimpleMessageLib newMsgLib = setupSimpleMessageLib(address(endpoint), remoteEid, false);

        vm.prank(receiver);
        endpoint.setReceiveLibrary(receiver, remoteEid, address(newMsgLib), 0);

        vm.roll(10);
        vm.prank(receiver);
        endpoint.setReceiveLibraryTimeout(receiver, remoteEid, address(simpleMsgLib), 15);

        vm.roll(14);
        vm.prank(address(simpleMsgLib));
        endpoint.verify(Origin(remoteEid, senderB32, 1), receiver, payloadHash);
        assertEq(endpoint.inboundPayloadHash(receiver, remoteEid, senderB32, 1), payloadHash);

        vm.roll(15);
        vm.prank(address(simpleMsgLib));
        vm.expectRevert(Errors.LZ_InvalidReceiveLibrary.selector);
        endpoint.verify(Origin(remoteEid, senderB32, 2), receiver, payloadHash);

        vm.prank(address(newMsgLib));
        endpoint.verify(Origin(remoteEid, senderB32, 2), receiver, payloadHash);
        assertEq(endpoint.inboundPayloadHash(receiver, remoteEid, senderB32, 2), payloadHash);
    }

    function test_graceValidOldLibraryCanOverwriteNewPayloadOnSameNonce() public {
        SimpleMessageLib newMsgLib = setupSimpleMessageLib(address(endpoint), remoteEid, false);

        bytes32 guidA = keccak256("guid-a");
        bytes32 guidB = keccak256("guid-b");
        bytes32 guidC = keccak256("guid-c");

        bytes memory payloadA = abi.encodePacked(guidA, bytes("foo"));
        bytes memory payloadB = abi.encodePacked(guidB, bytes("foo"));
        bytes memory payloadC = abi.encodePacked(guidC, bytes("foo"));

        vm.roll(10);
        endpoint.setDefaultReceiveLibrary(remoteEid, address(newMsgLib), 5);

        vm.prank(address(newMsgLib));
        endpoint.verify(Origin(remoteEid, senderB32, 1), receiver, keccak256(payloadB));
        assertEq(endpoint.inboundPayloadHash(receiver, remoteEid, senderB32, 1), keccak256(payloadB));

        vm.prank(address(simpleMsgLib));
        endpoint.verify(Origin(remoteEid, senderB32, 1), receiver, keccak256(payloadC));
        assertEq(endpoint.inboundPayloadHash(receiver, remoteEid, senderB32, 1), keccak256(payloadC));

        endpoint.lzReceive(Origin(remoteEid, senderB32, 1), receiver, guidC, bytes("foo"), "");
        assertEq(endpoint.inboundPayloadHash(receiver, remoteEid, senderB32, 1), bytes32(0));

        assertTrue(keccak256(payloadA) != keccak256(payloadB));
        assertTrue(keccak256(payloadB) != keccak256(payloadC));
    }
}
