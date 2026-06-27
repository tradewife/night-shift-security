// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "../../library/SettlementPools.sol";

/// @title Events emitted by a pool
/// @notice Contains all events emitted by the pool
interface ISettlementPoolEvents {

    /// @notice Emitted when a USDC deposits are made on behalf of both parties (atomically)
    /// @param poolAddress The address of the pool
    /// @param partyOneAddress The address that made the deposit
    /// @param partyTwoAddress The address belonging to other company
    /// @param partyOneAmountRequested The amount of USDC tokens deposited by party one
    /// @param partyTwoAmountRequested The amount of USDC tokens deposited by party two
    /// @param rfqUuid GUUID associated with RFQ (optional)
    /// @param parentQuoteUuid GUUID associated with quote (optional)
    event DepositedAtomic(
        address indexed poolAddress,
        address indexed partyOneAddress,
        address indexed partyTwoAddress,
        uint256 partyOneAmountRequested,
        uint256 partyTwoAmountRequested,
        uint128 rfqUuid,
        uint128 parentQuoteUuid
    );

    /// @notice Emitted when a USDC deposits are made on behalf of multiple parties (atomically)
    /// @param poolAddress The address of the pool
    /// @param creatorAddress The address that made the deposit
    /// @param creatorPartyAmountRequested The amount of USDC tokens deposited by party one
    /// @param items Other sides of the deposit
    event BatchDepositedAtomic(
        address indexed poolAddress,
        address indexed creatorAddress,
        uint256 creatorPartyAmountRequested,
        SettlementPools.AtomicDepositBatchItem[] items
    );

    /// @notice Emitted when a USDC deposit is made by a party to the pool
    /// @param poolAddress The address of the pool
    /// @param payer The address that made the deposit
    /// @param amount The amount of USDC tokens deposited
    /// @param transferUuid The UUID associated with (pending) deposit
    event Deposited(
        address indexed poolAddress,
        address indexed payer,
        uint256 amount,
        uint128 transferUuid
    );

    /// @notice Emitted when a USDC withdrawal is made by a party from the pool
    /// @param poolAddress The address of the pool
    /// @param payee The address that made the withdrawal
    /// @param amount The amount of USDC tokens withdrawn
    /// @param transferUuid The UUID associated with (pending) withdrawal
    event Withdrawn(
        address indexed poolAddress,
        address indexed payee,
        uint256 amount,
        uint128 transferUuid
    );

    /// @notice Emitted when a USDC withdrawal is made by a party from the pool
    /// @param poolAddress The address of the pool
    /// @param otherAddress The address of the added party
    event OtherPartyAdded(
        address indexed poolAddress,
        address indexed otherAddress
    );
}
