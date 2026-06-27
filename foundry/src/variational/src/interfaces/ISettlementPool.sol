// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "./pool/ISettlementPoolMembers.sol";
import "./pool/ISettlementPoolEvents.sol";

/// @title An interface for the core settlement pool
/// @notice A settlement pool facilitates the depositing and withdrawal of collateral by two parties,
/// based upon a set of positions that are held by the pool
/// @dev The pool interface is broken up into many smaller pieces
interface ISettlementPool is
ISettlementPoolMembers,
    ISettlementPoolEvents
{
    /// @notice Checks whether an address is a party in the pool
    /// @return Check result
    function checkOtherAddress(address addr) external view returns (bool);
}
