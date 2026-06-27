// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

/// @title An interface for a contract that is capable of deploying settlement pools
/// @notice A contract that constructs a settlement pool must implement this to pass arguments to the pool
/// @dev This is used to avoid having constructor arguments in the pool contract, which results in the init code hash
/// of the pool being constant allowing the CREATE2 address of the pool to be cheaply computed on-chain
interface ISettlementPoolDeployer {
    /// @notice Get the parameters to be used in constructing the pool, set transiently during pool creation.
    /// @dev Called by the pool constructor to fetch the parameters of the pool
    /// Returns factory The factory address
    /// Returns party0 The first party of the pool by address sort order
    /// Returns party1 The second party of the pool by address sort order
    /// Returns poolUuid The UUID associated with the (pending) settlement pool being deployed
    function parameters()
        external
        view
        returns (
            address factory,
            address creatorAddress,
            address[] calldata otherAddresses,
            uint128 poolUuid
        );
}
