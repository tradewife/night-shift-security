// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

library TreasuryManagement {
    struct Deposit {
        uint128 poolUuid;
        uint128 transferUuid;
        uint256 amountRequested;
    }
    struct Withdrawal {
        uint128 poolUuid;
        uint128 transferUuid;
        uint256 amountRequested;
    }
}