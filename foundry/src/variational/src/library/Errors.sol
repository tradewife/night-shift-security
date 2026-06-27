// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.10;

library Errors {
    struct ProcessingError {
        uint128 requestId;
        string failureReason;
    }
}
