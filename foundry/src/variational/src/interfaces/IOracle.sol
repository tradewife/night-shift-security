// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "./oracle/IOracleActions.sol";
import "./oracle/IOracleOwnerActions.sol";
import "./oracle/IOracleEvents.sol";

/// @title An interface for the oracle contract
/// @notice An oracle contract facilitates the aggregation of data from multiple providers
/// which respond to off-chain requests for data
/// @dev The oracle interface is broken up into many smaller pieces
interface IOracle is
    IOracleActions,
    IOracleOwnerActions,
    IOracleEvents
{
    /// @notice Returns the address of the configured factory
    function factory() external view returns (ISettlementPoolFactory);
}
