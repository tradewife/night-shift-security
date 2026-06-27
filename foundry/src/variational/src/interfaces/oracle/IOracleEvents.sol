// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "../../library/Fees.sol";
import "../../library/Errors.sol";
import {TreasuryManagement} from "../../library/TreasuryManagement.sol";

interface IOracleEvents {
    event FactoryUpdated(address factoryAddress);
    event ProviderAdded(address providerAddress);
    event ProviderRemoved(address providerAddress);
    event MinQuorumChanged(uint256 threshold);


    /// @notice Emitted when a fee batch has been processed
    /// @param successes requests that were claimed successfully
    /// @param failures requests that could not be claimed
    event FeeBatchProcessed(
        Fees.CollectionRequest[] successes,
        Errors.ProcessingError[] failures
    );

    /// @notice Emitted when a fee batch has been processed
    /// @param successes requests that were claimed successfully
    /// @param failures requests that could not be claimed
    event TreasuryManagementDepositsProcessed(
        Fees.CollectionRequest[] successes,
        Errors.ProcessingError[] failures
    );

    /**
     * @dev Emitted when deposit requests are processed.
     * @param requestor The address initiating the deposits.
     * @param successes An array of transfer UUIDs where deposits succeeded.
     * @param failures An error with description per withdrawal failure.
     */
    event DepositsProcessed(
        address indexed requestor,
        uint128[] successes,
        Errors.ProcessingError[] failures
    );

    /**
     * @dev Emitted when withdrawal requests are processed.
     * @param requestor The address initiating the withdrawals.
     * @param successes An array of transfer UUIDs where withdrawals succeeded.
     * @param failures An error with description per withdrawal failure.
     */
    event WithdrawalsProcessed(
        address indexed requestor,
        uint128[] successes,
        Errors.ProcessingError[] failures
    );

    event OLPToPoolTransfer(
        address indexed olpWallet,
        address indexed poolAddress,
        uint128 poolUuid,
        uint256 amount,
        uint128 rfqUuid,
        uint128 parentQuoteUuid
    );
}
