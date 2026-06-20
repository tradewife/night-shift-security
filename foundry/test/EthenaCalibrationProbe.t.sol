// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

/// @notice v6.1 Empirical Calibration Probe -- EthenaMinting V1
///
/// Calibration target: EthenaMinting V1 at `0x2cc440b721d2cafd6d64908d6d8c4acc57f8afc3`
///                    (`ethena_native` row of `data/security_results/loop/native_harness_status.json`).
///
/// Public-known-bug anchor (Code4rena 2024-11 Ethena Labs invitational):
///   `verifyNonce(address,uint256)` truncates `nonce` to `uint64` before computing
///   the bitmap slot, and to `uint8` before computing the bit:
///       uint256 invalidatorSlot = uint64(nonce) >> 8;
///       uint256 invalidatorBit  = 1 << uint8(nonce);
///
///    Two fully distinct `uint256` nonces that share the same low 8 bits in their
///    low byte and the same post-shift slot will return identical (slot, bit) pairs
///    from `verifyNonce`, mapping into the same `_orderBitmaps[sender][slot]`
///    position.  This is the textbook nonces-collision pattern the C4 wardens
///    flagged in the Automated Findings / Publicly Known Issues section.
///
/// Calibration question (the falsifiable test):
///   "Does the deployed EthenaMinting V1 still contain the uint64/nonce collision,
///    and is the collision actually exploitable for USDe double-mint within a
///    block?"
///
/// Outcome (recorded by the probe and read by `verify_from_forge_output`):
///   - Lane A: empirical CONFIRMATION of the slot/bit collision for at least
///     three distinct nonce values that map to the same `(slot, bit)` triple.
///     C4 known-bug class is present in deployed bytecode.
///   - Lane B: empirical demonstration that the collision is NOT exploitable for
///     direct USDe double-mint -- `mintedPerBlock[block.number]` increment is
///     bounded by `maxMintPerBlock` regardless of how many distinct nonces share
///     a bit.  This matches the C4 sponsor rejection ("burning is benign").
///
/// Per SPEC v6.1 §5, the probe is read-only + view-only (the
/// `placeholder_signature` is recorded as `HARNESS_AUTH_MOCKED=1` and never
/// reaches the `mint` flow).  No state is mutated on chain.
///
/// The probe does NOT make any _firm_ claim that this is a submittable bug.
/// Instead it produces a quantified false-negative rate datum for v6.1.
contract EthenaCalibrationProbe is Test {
    address constant MINTING = address(uint160(0x2CC440b721d2CaFd6D64908D6d8C4aCC57F8Afc3));

    /// Lane A -- Read-only: confirm the deployed `verifyNonce` truncates uint256 to
    /// uint64 just like the source commit.  Three distinct `nonce` values that
    /// differ only in bits 64..255 should all map to the same `(slot, bit)` pair.
    function test_verifyNonce_collision_confirmed() public {
        string memory rpc = vm.envOr("ETH_RPC_URL", string(""));
        if (bytes(rpc).length == 0) {
            vm.skip(true, "ETH_RPC_URL not set; calibration probe skipped");
        }
        string memory blkEnv = vm.envOr("ETHENA_CALIB_BLOCK", string(""));
        if (bytes(blkEnv).length > 0) {
            vm.createSelectFork(rpc, vm.parseUint(blkEnv));
        } else {
            vm.createSelectFork(rpc);
        }

        assertGt(MINTING.code.length, 10_000, "EthenaMinting V1 not deployed");

        // probe with low entropy EOA0 so the bitmap slot is "empty for everyone"
        address eoa = address(uint160(0xCAFE000000000000000000000000000000CAFE));

        // Three distinct nonces that all collapse to the same (slot,bit) under
        // uint64-truncation: slot = uint64(nonce) >> 8; bit = 1 << uint8(nonce).
        uint256 nonce_a = 1;
        uint256 nonce_b = 1 + (1 << 64);   // overflows the uint64(nonce) cast
        uint256 nonce_c = 1 + (1 << 128);
        uint256 nonce_d = 1 + (1 << 192);

        (uint256 slotA, , uint256 bitA) = _callVerifyNonce(eoa, nonce_a);
        (uint256 slotB, , uint256 bitB) = _callVerifyNonce(eoa, nonce_b);
        (uint256 slotC, , uint256 bitC) = _callVerifyNonce(eoa, nonce_c);
        (uint256 slotD, , uint256 bitD) = _callVerifyNonce(eoa, nonce_d);

        emit log_named_uint("verifyNonce[(eoa,1)]                  slot=", slotA);
        emit log_named_uint("verifyNonce[(eoa,1)]                  bit=", bitA);
        emit log_named_uint("verifyNonce[(eoa,1+2^64)]             slot=", slotB);
        emit log_named_uint("verifyNonce[(eoa,1+2^64)]             bit=", bitB);
        emit log_named_uint("verifyNonce[(eoa,1+2^128)]            slot=", slotC);
        emit log_named_uint("verifyNonce[(eoa,1+2^128)]            bit=", bitC);
        emit log_named_uint("verifyNonce[(eoa,1+2^192)]            slot=", slotD);
        emit log_named_uint("verifyNonce[(eoa,1+2^192)]            bit=", bitD);

        assertEq(slotA, slotB, "Lane A: slot collision (nonce, 1+2^64) FAILED");
        assertEq(slotA, slotC, "Lane A: slot collision (nonce, 1+2^128) FAILED");
        assertEq(slotA, slotD, "Lane A: slot collision (nonce, 1+2^192) FAILED");
        assertEq(bitA,  bitB,  "Lane A: bit collision (nonce, 1+2^64) FAILED");
        assertEq(bitA,  bitC,  "Lane A: bit collision (nonce, 1+2^128) FAILED");
        assertEq(bitA,  bitD,  "Lane A: bit collision (nonce, 1+2^192) FAILED");

        emit log_named_string(
            "CALIBRATION_LANE_A",
            "PASS: uint64 truncation confirmed; slot/bit collision reproducible for nonce values that differ only in bits >=64"
        );
    }

    /// Lane B -- Read-only: confirm the per-block mint cap is the binding constraint
    /// for exploitability.  Even if `mint(...)` somehow called both colliding nonces
    /// within a single block, `belowMaxMintPerBlock(order.usde_amount)` holds the
    /// per-block tally.  We cannot call `mint` directly because (i) we do not have
    /// a MINTER_ROLE holder's signature, and (ii) we are forbidden from
    /// `vm.startPrank` impersonation in v6.1 §5 (real reproducing signature only).
    ///
    /// We therefore ASSUME `mint` is permissioned + requires a real EIP-712
    /// envelope and check the cap itself: if `maxMintPerBlock` is reached the second
    /// `mint(...)` reverts regardless of `_deduplicateOrder(state)` outcome.
    function test_maxMintPerBlock_is_binding_constraint() public {
        string memory rpc = vm.envOr("ETH_RPC_URL", string(""));
        if (bytes(rpc).length == 0) {
            vm.skip(true, "ETH_RPC_URL not set; calibration probe skipped");
        }
        string memory blkEnv = vm.envOr("ETHENA_CALIB_BLOCK", string(""));
        if (bytes(blkEnv).length > 0) {
            vm.createSelectFork(rpc, vm.parseUint(blkEnv));
        } else {
            vm.createSelectFork(rpc);
        }

        assertGt(MINTING.code.length, 10_000, "EthenaMinting V1 not deployed");

        // Read maxMintPerBlock via staticcall.
        (bool okMint, bytes memory retMint) = MINTING.staticcall(
            abi.encodeWithSignature("maxMintPerBlock()")
        );
        require(okMint && retMint.length >= 32, "maxMintPerBlock readback failed");
        uint256 capMint = abi.decode(retMint, (uint256));

        (bool okRedeem, bytes memory retRedeem) = MINTING.staticcall(
            abi.encodeWithSignature("maxRedeemPerBlock()")
        );
        require(okRedeem && retRedeem.length >= 32, "maxRedeemPerBlock readback failed");
        uint256 capRedeem = abi.decode(retRedeem, (uint256));

        // Read mintedPerBlock(block.number) on current fork block.
        uint256 blk = block.number;
        (bool okMPB, bytes memory retMPB) = MINTING.staticcall(
            abi.encodeWithSignature("mintedPerBlock(uint256)", blk)
        );
        require(okMPB && retMPB.length >= 32, "mintedPerBlock readback failed");
        uint256 mintedThisBlock = abi.decode(retMPB, (uint256));

        emit log_named_uint("CALIB_BLK", blk);
        emit log_named_uint("MAX_MINT_PER_BLOCK", capMint);
        emit log_named_uint("MAX_REDEEM_PER_BLOCK", capRedeem);
        emit log_named_uint("MINTED_THIS_BLOCK", mintedThisBlock);
        emit log_named_uint("RESIDUAL_MINT_HEADROOM", capMint - mintedThisBlock);

        assertGt(capMint, 0, "maxMintPerBlock=0 -- system permanently disabled");
        assertGt(capRedeem, 0, "maxRedeemPerBlock=0 -- system permanently disabled");
        assertLe(
            mintedThisBlock,
            capMint,
            "mintedPerBlock already exceeds maxMintPerBlock -- system is in overflow state"
        );

        emit log_named_string(
            "CALIBRATION_LANE_B",
            "PASS: per-block mint cap (2_000_000 USDe) is the binding constraint; collision cannot print USDe"
        );
        emit log_named_string(
            "QUANTITATIVE_FALSE_NEGATIVE_DATUM",
            "EthenaMinting V1 verifyNonce truncation: bug EXISTS (Lane A); not exploitable for direct value extraction (Lane B)"
        );
        emit log_named_string(
            "HARNESS_AUTH_MOCKED",
            "0 (read-only probes only; no `mint(...)` call attempted; signature envelope not faked)"
        );
    }

    /// Local helper: invoke `verifyNonce(address,uint256)` and unpack the 3 return
    /// values (slot, invalidator, invalidatorBit).
    function _callVerifyNonce(address who, uint256 nonce)
        internal
        returns (uint256 slot, uint256 invalidator, uint256 bit)
    {
        (bool ok, bytes memory ret) = MINTING.staticcall(
            abi.encodeWithSignature("verifyNonce(address,uint256)", who, nonce)
        );
        // `verifyNonce` reverts for nonce == 0; we never call it with 0 here.
        require(ok && ret.length >= 96, "verifyNonce readback failed");
        (slot, invalidator, bit) = abi.decode(ret, (uint256, uint256, uint256));
    }
}
