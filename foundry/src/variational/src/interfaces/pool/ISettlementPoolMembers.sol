// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "../IOracle.sol";

/// @title Pool state that never changes
/// @notice These parameters are fixed for a pool forever, i.e., the methods will always return the same values
interface ISettlementPoolMembers {
    /// @notice The contract that deployed the pool, which must adhere to the ISettlementPoolDeployer interface
    /// @return The contract address
    function factory() external view returns (address);

    /// @notice The first of the parties to the pool
    /// @return The party wallet address
    function creatorAddress() external view returns (address);

    /// @notice The UUID associated with this pool
    /// @return The pool's UUID
    function poolUuid() external view returns (uint128);
}
