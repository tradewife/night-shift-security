// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

library Fees {
    struct CollectionRequest {
        uint128 poolUuid;
        uint256 amountRequested;
        uint128 feesBatchId;
    }
}
