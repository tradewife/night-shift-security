// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "lib/openzeppelin-contracts/contracts/access/AccessControl.sol";
import "lib/openzeppelin-contracts/contracts/security/ReentrancyGuard.sol";
import "lib/openzeppelin-contracts/contracts/security/Pausable.sol";
import "lib/openzeppelin-contracts/contracts/token/ERC20/extensions/draft-ERC20Permit.sol";
import "./interfaces/IOracle.sol";
import "./SettlementPool.sol";
import "./interfaces/ISettlementPoolFactory.sol";
import "./library/Fees.sol";
import "./library/Errors.sol";
import "./library/TreasuryManagement.sol";
import "./library/SettlementPools.sol";

contract Oracle is AccessControl, ReentrancyGuard, IOracle, Pausable {
    bytes32 public constant PROVIDER_ROLE = keccak256("PROVIDER_ROLE");
    ISettlementPoolFactory public override factory;
    uint256 private numProviders = 0;

    mapping(uint128 => address) private pools;
    mapping(uint128 => bool) public atomic_deposits_processed;

    constructor() {
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender); // make the deployer admin
    }

    function collectFees(
        Fees.CollectionRequest[] memory requests
    ) external override nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        (
            Fees.CollectionRequest[] memory successfulRequests,
            Errors.ProcessingError[] memory failedRequests,
            uint successCount,
            uint failureCount
        ) = _processFeeRequests(requests);

        // Emit results
        emit FeeBatchProcessed(
            _truncateCollectionRequestsArray(successfulRequests, successCount),
            _truncateProcessingErrorsArray(failedRequests, failureCount)
        );
    }

    /**
     * @notice Truncates an array of CollectionRequest structs to the specified length.
     * @param array The array to truncate.
     * @param length The desired length.
     * @return A new array containing the truncated CollectionRequest structs.
     */
    function _truncateCollectionRequestsArray(
        Fees.CollectionRequest[] memory array,
        uint length
    ) internal pure returns (Fees.CollectionRequest[] memory) {
        Fees.CollectionRequest[] memory truncated = new Fees.CollectionRequest[](length);
        for (uint i = 0; i < length; i++) {
            truncated[i] = array[i];
        }
        return truncated;
    }


    /**
     * @notice Truncates an array of FeeProcessingError structs to the specified length.
     * @param array The array to truncate.
     * @param length The desired length.
     * @return A new array containing the truncated FeeProcessingError structs.
     */
    function _truncateProcessingErrorsArray(
        Errors.ProcessingError[] memory array,
        uint length
    ) internal pure returns (Errors.ProcessingError[] memory) {
        Errors.ProcessingError[] memory truncated = new Errors.ProcessingError[](length);
        for (uint i = 0; i < length; i++) {
            truncated[i] = array[i];
        }
        return truncated;
    }


    /**
     * @notice Processes fee collection requests.
     * @param requests The collection requests to process.
     * @return successfulRequests Truncated array of successful requests.
     * @return failedRequests Truncated array of failed requests with reasons.
     * @return successCount The number of successful requests.
     * @return failureCount The number of failed requests.
     */
    function _processFeeRequests(
        Fees.CollectionRequest[] memory requests
    ) internal returns (
        Fees.CollectionRequest[] memory successfulRequests,
        Errors.ProcessingError[] memory failedRequests,
        uint successCount,
        uint failureCount
    ) {
        successfulRequests = new Fees.CollectionRequest[](requests.length);
        failedRequests = new Errors.ProcessingError[](requests.length);
        successCount = 0;
        failureCount = 0;

        for (uint i = 0; i < requests.length; i++) {
            address poolAddress = factory.getPool(requests[i].poolUuid);
            require(poolAddress != address(0), "no pool mapping found for given poolUuid");

            try SettlementPool(poolAddress).withdrawFees(
                msg.sender, // only provider role can withdraw
                requests[i].amountRequested,
                requests[i].feesBatchId
            ) {
                successfulRequests[successCount] = requests[i];
                successCount++;
            } catch Error(string memory reason) {
                failedRequests[failureCount] = Errors.ProcessingError({
                    requestId: requests[i].feesBatchId,
                    failureReason: reason
                });
                failureCount++;
            } catch {
                failedRequests[failureCount] = Errors.ProcessingError({
                    requestId: requests[i].feesBatchId,
                    failureReason: "low-level error"
                });
                failureCount++;
            }
        }

        return (
            successfulRequests,
            failedRequests,
            successCount,
            failureCount
        );
    }


    /**
     * @notice Processes a batch of deposit requests for a single requestor.
     * @param requestor The address for which the deposits are made.
     * @param deposits The deposit requests to process.
     */
    function processTreasuryManagementDeposits(
        address requestor,
        TreasuryManagement.Deposit[] memory deposits
    ) external nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        uint depositsLength = deposits.length;

        uint128[] memory successfulTransferUuids = new uint128[](depositsLength);
        Errors.ProcessingError[] memory failedTransfers = new Errors.ProcessingError[](depositsLength);
        uint successCount = 0;
        uint failureCount = 0;

        for (uint i = 0; i < depositsLength; i++) {
            address poolAddress = factory.getPool(deposits[i].poolUuid);
            require(poolAddress != address(0), "Invalid poolUuid");

            try SettlementPool(poolAddress).depositUSDCNoEvent(
                requestor,
                deposits[i].amountRequested,
                deposits[i].transferUuid
            ) {
                successfulTransferUuids[successCount] = deposits[i].transferUuid;
                successCount++;
            } catch Error(string memory reason) {
                failedTransfers[failureCount] = Errors.ProcessingError({
                    requestId: deposits[i].transferUuid,
                    failureReason: reason
                });
                failureCount++;
            } catch {
                failedTransfers[failureCount] = Errors.ProcessingError({
                    requestId: deposits[i].transferUuid,
                    failureReason: "low-level error"
                });
                failureCount++;
            }
        }

        emit DepositsProcessed(
            requestor,
            _truncateUint128Array(successfulTransferUuids, successCount),
            _truncateProcessingErrorsArray(failedTransfers, failureCount)
        );
    }

    /**
     * @notice Processes a batch of withdrawal requests for a single requestor.
     * @param requestor The address for which the withdrawals are made.
     * @param withdrawals The withdrawal requests to process.
     */
    function processTreasuryManagementWithdrawals(
        address requestor,
        TreasuryManagement.Withdrawal[] memory withdrawals
    ) external nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        uint withdrawalsLength = withdrawals.length;

        uint128[] memory successfulTransferUuids = new uint128[](withdrawalsLength);
        Errors.ProcessingError[] memory failedTransfers = new Errors.ProcessingError[](withdrawalsLength);
        uint successCount = 0;
        uint failureCount = 0;

        for (uint i = 0; i < withdrawalsLength; i++) {
            address poolAddress = factory.getPool(withdrawals[i].poolUuid);
            require(poolAddress != address(0), "Invalid poolUuid");

            try SettlementPool(poolAddress).withdrawUSDCNoEvent(
                requestor,
                withdrawals[i].amountRequested,
                withdrawals[i].transferUuid
            ) {
                successfulTransferUuids[successCount] = withdrawals[i].transferUuid;
                successCount++;
            } catch Error(string memory reason) {
                failedTransfers[failureCount] = Errors.ProcessingError({
                    requestId: withdrawals[i].transferUuid,
                    failureReason: reason
                });
                failureCount++;
            } catch {
                failedTransfers[failureCount] = Errors.ProcessingError({
                    requestId: withdrawals[i].transferUuid,
                    failureReason: "low-level error"
                });
                failureCount++;
            }
        }

        emit WithdrawalsProcessed(
            requestor,
            _truncateUint128Array(successfulTransferUuids, successCount),
            _truncateProcessingErrorsArray(failedTransfers, failureCount)
        );
    }

    /**
     * @notice Truncates an array of uint128 values to the specified length.
     * @param array The array to truncate.
     * @param length The desired length.
     * @return A new array containing the truncated values.
     */
    function _truncateUint128Array(
        uint128[] memory array,
        uint length
    ) internal pure returns (uint128[] memory) {
        uint128[] memory truncated = new uint128[](length);
        for (uint i = 0; i < length; i++) {
            truncated[i] = array[i];
        }
        return truncated;
    }

    function withdrawUSDC(
        address requestor,
        uint256 amountRequested,
        uint128 poolUuid,
        uint128 transferUuid
    ) external override nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        address poolAddress = getPool(poolUuid);
        SettlementPool pool = SettlementPool(poolAddress);
        pool.withdrawUSDC(
            requestor,
            amountRequested,
            transferUuid
        );
    }

    function transferFromOLPToPool(
        address olpWallet,
        address poolAddress,
        uint256 amount,
        uint128 poolUuid,
        uint128 rfqUuid,
        uint128 parentQuoteUuid
    ) external nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        require(olpWallet != address(0), "Oracle: OLP wallet address cannot be zero");
        require(poolAddress != address(0), "Oracle: SettlementPool address cannot be zero");
        require(amount > 0, "Oracle: Transfer amount must be greater than zero");

        IERC20 usdc = factory.usdcAddress();
        bool fromSuccess = usdc.transferFrom(olpWallet, address(this), amount);
        require(fromSuccess, "Vault: Transfer from OLP wallet failed");
        bool toSuccess = usdc.transfer(poolAddress, amount);
        require(toSuccess, "Vault: Transfer to Settlement Pool failed");
        emit OLPToPoolTransfer(olpWallet, poolAddress, poolUuid, amount, rfqUuid, parentQuoteUuid);
    }

    function atomicDeposit(
        address partyOneAddress,
        address partyTwoAddress,
        uint256 partyOneAmountRequested,
        uint256 partyTwoAmountRequested,
        uint128 poolUuid,
        uint128 rfqUuid,
        uint128 parentQuoteUuid
    ) external override nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        address poolAddress = getPool(poolUuid);
        SettlementPool pool = SettlementPool(poolAddress);
        if (partyOneAmountRequested > 0 && partyTwoAmountRequested == 0) {
            require(atomic_deposits_processed[parentQuoteUuid] == false, "this transfer has already been processed");
            IERC20 usdc = factory.usdcAddress();
            bool fromSuccess = usdc.transferFrom(partyOneAddress, address(this), partyOneAmountRequested);
            require(fromSuccess, "Transfer from creator wallet failed");
            bool toSuccess = usdc.transfer(poolAddress, partyOneAmountRequested);
            require(toSuccess, "Transfer to Settlement Pool failed");
            if (parentQuoteUuid != 0) {
                atomic_deposits_processed[parentQuoteUuid] = true;
            }
        }
        require(
            (partyOneAddress == pool.creatorAddress() && pool.checkOtherAddress(partyTwoAddress)) ||
            (pool.checkOtherAddress(partyOneAddress) && partyTwoAddress == pool.creatorAddress()),
            "incorrect addresses provided"
        );
        pool.depositUSDCAtomic(
            partyOneAddress,
            partyTwoAddress,
            partyOneAmountRequested,
            partyTwoAmountRequested,
            rfqUuid,
            parentQuoteUuid
        );
    }

    function batchAtomicDeposit(
        uint128 poolUuid,
        address creatorPartyAddress,
        uint256 creatorPartyAmountRequested,
        SettlementPools.AtomicDepositBatchItem[] calldata items
    ) external override nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        address poolAddress = factory.getPool(poolUuid);
        require(poolAddress != address(0), "no pool mapping found for given poolUuid");
        SettlementPool pool = SettlementPool(poolAddress);
        require((creatorPartyAddress == pool.creatorAddress()), "incorrect creator address provided");
        for (uint i = 0; i < items.length; i++) {
            require(pool.checkOtherAddress(items[i].otherPartyAddress), "incorrect other address provided");
        }
        pool.batchDepositUSDCAtomic(
            creatorPartyAddress,
            creatorPartyAmountRequested,
            items
        );
    }

    function depositUSDC(
        address sender,
        uint256 amount,
        uint128 poolUuid,
        uint128 transferUuid
    ) external override nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        address poolAddress = getPool(poolUuid);
        SettlementPool pool = SettlementPool(poolAddress);
        pool.depositUSDCOnBehalfOfParty(
            sender,
            amount,
            transferUuid
        );
    }

    function createPool(
        address creatorAddress,
        address[] calldata otherAddresses,
        uint128 poolUuid,
        uint128 rfqUuid,
        uint128 parentQuoteUuid,
        address feePaidBy,
        uint256 feeAmount
    ) external override nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        require(pools[poolUuid] == address(0), "Pool already exists for the given UUID");
        address poolAddress = factory.createPool(
            creatorAddress,
            otherAddresses,
            poolUuid,
            rfqUuid,
            parentQuoteUuid,
            msg.sender,
            feePaidBy,
            feeAmount
        );
        pools[poolUuid] = poolAddress;
    }

    function addOtherParty(
        uint128 poolUuid,
        address otherAddress
    ) external override nonReentrant whenNotPaused onlyRole(PROVIDER_ROLE) {
        address poolAddress = factory.getPool(poolUuid);
        require(poolAddress != address(0), "no pool mapping found for given poolUuid");
        SettlementPool pool = SettlementPool(poolAddress);
        pool.addOtherParty(otherAddress);
    }

    function setSettlementPoolFactory(
        address factoryAddress
    ) external override nonReentrant whenNotPaused onlyRole(DEFAULT_ADMIN_ROLE) {
        require(factoryAddress != address(0), "Factory address cannot be zero");
        require(factoryAddress != address(factory), "New factory must be different");
        factory = ISettlementPoolFactory(factoryAddress);
        emit FactoryUpdated(factoryAddress);
    }

    function getPool(uint128 poolUuid) public view returns (address) {
        address poolAddress = pools[poolUuid];
        require(poolAddress != address(0), "Pool not found for the given UUID");
        return poolAddress;
    }

    // Owner admin functions
    function addProvider(
        address provider
    ) external override nonReentrant whenNotPaused onlyRole(DEFAULT_ADMIN_ROLE) {
        require(
            !hasRole(PROVIDER_ROLE, provider),
            "Oracle: Provider already added."
        );

        _grantRole(PROVIDER_ROLE, provider);
        numProviders++;

        emit ProviderAdded(provider);
    }

    function removeProvider(
        address provider
    ) external override nonReentrant whenNotPaused onlyRole(DEFAULT_ADMIN_ROLE) {
        require(
            hasRole(PROVIDER_ROLE, provider),
            "Oracle: Address is not a recognized provider."
        );
        require(numProviders > 1, "Oracle: Cannot remove the only provider.");

        _revokeRole(PROVIDER_ROLE, provider);
        numProviders--;

        emit ProviderRemoved(provider);
    }

    // Override grantRole to ensure numProviders is updated when PROVIDER_ROLE is granted
    function grantRole(bytes32 role, address account) public override whenNotPaused onlyRole(getRoleAdmin(role)) {
        super.grantRole(role, account);

        if (role == PROVIDER_ROLE) {
            require(!hasRole(PROVIDER_ROLE, account), "Oracle: Provider already added.");
            numProviders++;
            emit ProviderAdded(account);
        }
    }

    // Override revokeRole to ensure numProviders is updated when PROVIDER_ROLE is revoked
    function revokeRole(bytes32 role, address account) public override whenNotPaused onlyRole(getRoleAdmin(role)) {
        if (role == PROVIDER_ROLE) {
            require(hasRole(PROVIDER_ROLE, account), "Oracle: Address is not a recognized provider.");
            require(numProviders > 1, "Oracle: Cannot remove the only provider.");
            numProviders--;
            emit ProviderRemoved(account);
        }
        super.revokeRole(role, account);
    }

    // Allows Default Admin to pause the contract
    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    // Allows Default Admin to unpause the contract
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}