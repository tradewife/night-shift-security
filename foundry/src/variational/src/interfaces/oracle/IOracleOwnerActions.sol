// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

interface IOracleOwnerActions {
    // TODO: docs
    function addProvider(address provider) external;

    function setSettlementPoolFactory(address factoryAddress) external;

    function removeProvider(address provider) external;

    // Allows Default Admin to pause the contract
    function pause() external;

    // Allows Default Admin to unpause the contract
    function unpause() external;
}
