// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "../ISettlementPoolFactory.sol";
import "../../library/Fees.sol";
import "../../library/TreasuryManagement.sol";
import "../../library/SettlementPools.sol";

interface IOracleActions {

    function createPool(
        address creatorAddress,
        address[] calldata otherAddresses,
        uint128 poolUuid,
        uint128 rfqUuid,
        uint128 parentQuoteUuid,
        address feePaidBy,
        uint256 feeAmount
    ) external;

    function depositUSDC(
        address sender,
        uint256 amount,
        uint128 poolUuid,
        uint128 transferUuid
    ) external;

    function atomicDeposit(
        address partyOneAddress,
        address partyTwoAddress,
        uint256 partyOneAmountRequested,
        uint256 partyTwoAmountRequested,
        uint128 poolUuid,
        uint128 rfqUuid,
        uint128 parentQuoteUuid
    ) external;

    function batchAtomicDeposit(
        uint128 poolUuid,
        address creatorPartyAddress,
        uint256 creatorPartyAmountRequested,
        SettlementPools.AtomicDepositBatchItem[] calldata items
    ) external;

    function collectFees(
        Fees.CollectionRequest[] memory requests
    ) external;

    function processTreasuryManagementWithdrawals(
        address requestor,
        TreasuryManagement.Withdrawal[] memory withdrawals
    ) external;

    function transferFromOLPToPool(
        address olpWallet,
        address poolAddress,
        uint256 amount,
        uint128 poolUuid,
        uint128 rfqUuid,
        uint128 parentQuoteUuid
    ) external;

    function withdrawUSDC(
        address requestor,
        uint256 amountRequested,
        uint128 poolUuid,
        uint128 transferUuid
    ) external;

    function addOtherParty(
        uint128 poolUuid,
        address otherAddress
    ) external;
}
