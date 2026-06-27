// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

library SettlementPools {
    struct AtomicDepositBatchItem {
        address otherPartyAddress;
        uint256 otherPartyAmountRequested;
        uint128 rfqUuid;
        uint128 parentQuoteUuid;
    }
}
