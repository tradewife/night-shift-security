// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "lib/openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";
import "./IOracle.sol";

/// @title The interface for the settlement pool Factory
/// @notice The settlement pool Factory facilitates creation of settlement pools and control over pool configurations
interface ISettlementPoolFactory {
    /// @notice Returns the address of the configured oracle
    function oracle() external view returns (IOracle);

    /// @notice Returns the address of the configured USDC contract
    function usdcAddress() external view returns (IERC20);

    /// @notice Returns the address of the owner of the factory
    function getOwner() external view returns (address);

    /// @notice Emitted when a pool is created
    /// @param creatorAddress The creator of the desired settlement pool
    /// @param otherAddresses Other participants in the pool
    /// @param poolUuid A UUID associated with created settlement pool
    /// @param pool The address of the created pool
    /// @param rfqUuid GUUID associated with RFQ (optional)
    /// @param parentQuoteUuid GUUID associated with quote (optional)
    event PoolCreated(
        address indexed creatorAddress,
        address[] otherAddresses,
        uint128 indexed poolUuid,
        address pool,
        uint128 rfqUuid,
        uint128 parentQuoteUuid,
        address feePaidBy,
        uint256 feeAmount
    );

    /// @notice Emitted when the oracle address is updated
    event OracleAddressChanged(address newAddress);

    /// @notice Returns the settlement pool address for a given pool, given the assigned UUID
    /// @param poolUuid The UUID associated with this settlement pool
    /// @return pool The pool address
    function getPool(uint128 poolUuid) external view returns (address pool);

    /// @notice Creates a settlement pool for the given pair of counterparties
    /// @param creatorAddress Creator of the desired pool
    /// @param otherAddresses The other parties in the desired pool
    /// @param poolUuid The UUID associated with (pending) settlement pool
    /// @dev The call will revert if the pool already exists, the fee is invalid,
    // or the party arguments are invalid.
    /// @return pool The address of the newly created pool
    /// @param rfqUuid GUUID associated with RFQ (optional, only if pool is being created as part of RFQ flow)
    /// @param parentQuoteUuid GUUID associated with quote (optional, only if pool is being created as part of RFQ)
    function createPool(
        address creatorAddress,
        address[] calldata otherAddresses,
        uint128 poolUuid,
        uint128 rfqUuid,
        uint128 parentQuoteUuid,
        address feeRequestor,
        address feePaidBy,
        uint256 feeAmount
    ) external returns (address pool);
}
