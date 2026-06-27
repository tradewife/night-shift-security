// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "lib/openzeppelin-contracts/contracts/access/Ownable.sol";
import "lib/openzeppelin-contracts/contracts/proxy/Clones.sol";
import "./SettlementPool.sol";
import "./interfaces/ISettlementPoolFactory.sol";

/// @title Canonical Settlement Pool Factory
/// @notice Deploys and manages Settlement Pools with EIP-1167 Minimal Proxies
contract SettlementPoolFactory is ISettlementPoolFactory, Ownable {
    IOracle public override oracle;
    IERC20 public immutable override usdcAddress;
    address public immutable implementation; // Logic contract address

    mapping(uint128 => address) public override getPool;

    constructor(address _implementation, address _usdcAddress) {
        implementation = _implementation; // Shared logic contract for proxies
        usdcAddress = IERC20(_usdcAddress); // ERC20 token used in pools
    }

    /// @notice Deploys a new settlement pool
    function createPool(
        address creatorAddress,
        address[] calldata otherAddresses,
        uint128 poolUuid,
        uint128 rfqUuid,
        uint128 parentQuoteUuid,
        address feeRequestor,
        address feePaidBy,
        uint256 feeAmount
    ) external override returns (address pool) {
        require(
            msg.sender == owner() || msg.sender == address(oracle),
            "SettlementPoolFactory: caller must be owner or oracle"
        );
        require(
            creatorAddress != address(0),
            "SettlementPoolFactory: creatorAddress must be a non-zero address"
        );
        require(
            otherAddresses.length >= 1,
            "SettlementPoolFactory: at least two parties are required"
        );
        require(
            feeAmount == 0 || feeAmount > 0 && feeRequestor != address(0) && feePaidBy != address(0),
            "SettlementPoolFactory: feeRequestor and feePaidBy must be set if feeAmount > 0"
        );
        for (uint i = 0; i < otherAddresses.length; i++) {
            require(
                otherAddresses[i] != address(0),
                "SettlementPoolFactory: each party must have a non-zero address"
            );
            require(
                otherAddresses[i] != creatorAddress,
                "SettlementPoolFactory: parties must be different"
            );
            for (uint j = i + 1; j < otherAddresses.length; j++) {
                require(
                    otherAddresses[i] != otherAddresses[j],
                    "SettlementPoolFactory: parties must be different"
                );
            }
        }

        require(
            poolUuid != 0,
            "SettlementPoolFactory: poolUuid must be non-zero"
        );
        pool = getPool[poolUuid];
        require(
            pool == address(0),
            "SettlementPoolFactory: pool for uuid already exists"
        );

        if (feeAmount > 0) {
            try usdcAddress.transferFrom(feePaidBy, feeRequestor, feeAmount) {
            } catch {
                revert("SettlementPoolFactory: cannot withdraw creation fee");
            }
        }

        // Deploy a minimal proxy
        pool = Clones.clone(implementation);

        // Initialize the proxy
        SettlementPool(pool).initialize(
            creatorAddress,
            address(this),
            otherAddresses,
            poolUuid
        );

        // Store the pool in the mapping
        getPool[poolUuid] = pool;

        emit PoolCreated(creatorAddress, otherAddresses, poolUuid, pool, rfqUuid, parentQuoteUuid, feePaidBy, feeAmount);
    }


    /// @notice Updates the Oracle address
    function setOracleAddress(address newAddress) external onlyOwner {
        oracle = IOracle(newAddress);
        emit OracleAddressChanged(newAddress);
    }

    /// @inheritdoc ISettlementPoolFactory
    function getOwner() external view override returns (address) {
        return owner();
    }
}