// SPDX-License-Identifier: MIT
pragma solidity ^0.8.2;

import "lib/openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";
import "lib/openzeppelin-contracts/contracts/security/ReentrancyGuard.sol";
import "./interfaces/ISettlementPool.sol";
import "./interfaces/ISettlementPoolDeployer.sol";
import "./interfaces/ISettlementPoolFactory.sol";
import "./interfaces/IOracle.sol";
import "./library/SettlementPools.sol";

contract SettlementPool is ISettlementPool, ReentrancyGuard {
    /// @inheritdoc ISettlementPoolMembers
    address public override factory;
    /// @inheritdoc ISettlementPoolMembers
    address public override creatorAddress;
    /// @inheritdoc ISettlementPoolMembers
    uint128 public override poolUuid;

    // TODO: docs
    uint256 private randNonce = 0;
    mapping(address => bool) public otherAddresses;
    mapping(uint128 => bool) public transfers_processed;

    modifier onlyParties() {
        require(
            msg.sender == creatorAddress || otherAddresses[msg.sender],
            "SettlementPool: Unauthorized."
        );
        _;
    }

    modifier onlyFactoryOwner() {
        require(
            msg.sender == ISettlementPoolFactory(factory).getOwner(),
            "SettlementPool: Unauthorized."
        );
        _;
    }

    modifier onlyOracle() {
        require(
            msg.sender == address(_oracle()),
            "SettlementPool: Unauthorized."
        );
        _;
    }


    /// @notice Initialize the pool with its data
    function initialize(
        address _creatorAddress,
        address _factory,
        address[] calldata _otherAddresses,
        uint128 _poolUuid
    ) external nonReentrant  {
        require(msg.sender != address(0), "SettlementPool: Sender must be non-zero");
        require(msg.sender == address(ISettlementPoolFactory(_factory)), "SettlementPool: Only factory can initialize");
        require(factory == address(0), "SettlementPool: can only initialize once");
        require(_creatorAddress != address(0), "SettlementPool: Creator address must be non-zero");

        // Initialize state
        creatorAddress = _creatorAddress;
        poolUuid = _poolUuid;
        factory = _factory;

        for (uint256 i = 0; i < _otherAddresses.length; i++) {
            require(_otherAddresses[i] != address(0), "SettlementPool: Other address must be non-zero");
            otherAddresses[_otherAddresses[i]] = true;
        }
    }


    /// @dev Get the pool's balance of USDC
    /// @dev This function could be further optimized
    /// See https://github.com/Uniswap/v3-core/blob/main/contracts/UniswapV3Pool.sol#L140
    function _totalBalance() private view returns (uint256) {
        return _usdc().balanceOf(address(this));
    }

    function _oracle() private view returns (IOracle) {
        return ISettlementPoolFactory(factory).oracle();
    }

    function _usdc() private view returns (IERC20) {
        return ISettlementPoolFactory(factory).usdcAddress();
    }

    function _depositUSDCOnBehalf(
        address sender,
        uint256 amount,
        uint128 transferUuid,
        bool emitDepositedEvent
    ) private {
        require(amount > 0, "SettlementPool: Cannot deposit 0 USDC.");
        require(transfers_processed[transferUuid] == false, "this transfer has already been processed");
        uint256 allowance = _usdc().allowance(sender, address(this));
        require(
            allowance >= amount,
            "SettlementPool: You must approve the contract to transfer at least the amount you are trying to deposit."
        );

        // todo: We first should make sure that there is not negative equity in the pool before incrementing tokens owed
        try _usdc().transferFrom(sender, address(this), amount) {
            if (transferUuid != 0) {
                transfers_processed[transferUuid] = true;
            }
            if (emitDepositedEvent) {
                emit Deposited(address(this), sender, amount, transferUuid);
            }
        } catch {
            revert("SettlementPool: Could not deposit USDC.");
        }
    }

    /// @inheritdoc ISettlementPool
    function checkOtherAddress(address addr) external view override returns (bool) {
        return otherAddresses[addr];
    }

    function batchDepositUSDCAtomic(
        address creatorPartyAddress,
        uint256 creatorPartyAmountRequested,
        SettlementPools.AtomicDepositBatchItem[] calldata items
    ) external nonReentrant onlyOracle {
        for (uint i = 0; i < items.length; i++) {
            require(creatorPartyAmountRequested > 0 || items[i].otherPartyAmountRequested > 0, "SettlementPool: when creator amount is 0, all other amounts must be > 0");
            uint128 transferUuid = items[i].parentQuoteUuid;
            if (creatorPartyAmountRequested > 0) {
                _depositUSDCOnBehalf(
                    creatorPartyAddress,
                    creatorPartyAmountRequested,
                    transferUuid,
                    false /* emitDepositedEvent */
                );
                // we reset this to 0 now in case there is also a deposit required for the other company. We only
                // need to check dupes once per atomic deposit so by resetting this to 0 here the second deposit will
                // skip the dupe check
                transferUuid = 0;
            }
            if (items[i].otherPartyAmountRequested > 0) {
                _depositUSDCOnBehalf(
                    items[i].otherPartyAddress,
                    items[i].otherPartyAmountRequested,
                    transferUuid,
                    false /* emitDepositedEvent */
                );
            }
        }
        emit BatchDepositedAtomic(
            address(this),
            creatorPartyAddress,
            creatorPartyAmountRequested,
            items
        );
    }

    function depositUSDCAtomic(
        address partyOneAddress,
        address partyTwoAddress,
        uint256 partyOneAmountRequested,
        uint256 partyTwoAmountRequested,
        uint128 rfqUuid,
        uint128 parentQuoteUuid
    ) external nonReentrant onlyOracle {
        // if only the first party requested deposit we skip the rest and simply emit the event because
        // we already completed the single party transfer in the calling function
        if (partyOneAmountRequested > 0 && partyTwoAmountRequested == 0) {
            emit DepositedAtomic(
                address(this),
                partyOneAddress,
                partyTwoAddress,
                partyOneAmountRequested,
                partyTwoAmountRequested,
                rfqUuid,
                parentQuoteUuid
            );
            return;
        }
        require(parentQuoteUuid != 0, "SettlementPool: parentQuoteUuid must be non-zero");
        require(
            partyOneAmountRequested > 0 || partyTwoAmountRequested > 0,
            "one of the two deposit amounts must be non-zero"
        );
        uint128 transferUuid = parentQuoteUuid;
        if (partyOneAmountRequested > 0) {
            _depositUSDCOnBehalf(
                partyOneAddress,
                partyOneAmountRequested,
                transferUuid,
                false /* emitDepositedEvent */
            );
            // we reset this to 0 now in case there is also a deposit required for the other company. We only
            // need to check dupes once per atomic deposit so by resetting this to 0 here the second deposit will
            // skip the dupe check
            transferUuid = 0;
        }
        if (partyTwoAmountRequested > 0) {
            _depositUSDCOnBehalf(
                partyTwoAddress,
                partyTwoAmountRequested,
                transferUuid,
                false /* emitDepositedEvent */
            );
        }
        emit DepositedAtomic(
            address(this),
            partyOneAddress,
            partyTwoAddress,
            partyOneAmountRequested,
            partyTwoAmountRequested,
            rfqUuid,
            parentQuoteUuid
        );
    }

    // depositUSDC deposits USDC tokens to the settlement pool on behalf of creator or one of the other parties
    // TODO: here and below document check, effects, interact patter in each key function
    function depositUSDC(
        uint256 amount,
        uint128 transferUuid
    ) external nonReentrant onlyParties {
        require(transferUuid != 0, "SettlementPool: transferUuid must be non-zero");
        _depositUSDCOnBehalf(
            msg.sender,
            amount,
            transferUuid,
            true /* emitDepositedEvent */
        );
    }

    function depositUSDCOnBehalfOfParty(
        address sender,
        uint256 amount,
        uint128 transferUuid
    ) external nonReentrant onlyOracle {
        require(transferUuid != 0, "SettlementPool: transferUuid must be non-zero");
        _depositUSDCOnBehalf(
            sender,
            amount,
            transferUuid,
            true /* emitDepositedEvent */
        );
    }

    function withdrawFees(
        address requestor,
        uint256 amountRequested,
        uint128 fees_batch_id
    ) external nonReentrant onlyOracle {
        require(amountRequested > 0, "SettlementPool: Cannot withdraw 0 USDC.");
        require(fees_batch_id != 0, "must provide non-zero fees_batch_id");
        require(transfers_processed[fees_batch_id] == false, "this fees batch has already been processed");
        try _usdc().transfer(requestor, amountRequested) {
            transfers_processed[fees_batch_id] = true;
        } catch {
            revert("SettlementPool: Could not withdraw USDC.");
        }
    }

    function _withdrawUSDCOnBehalf(
        address requestor,
        uint256 amountRequested,
        uint128 transferUuid,
        bool emitDepositedEvent
    ) private {
        require(amountRequested > 0, "SettlementPool: Cannot withdraw 0 USDC.");
        require(transferUuid != 0, "must provide non-zero transferUuid");
        require(
            requestor == creatorAddress || otherAddresses[requestor] == true,
            "requestor must be one of creatorCompany or otherCompany"
        );
        require(transfers_processed[transferUuid] == false, "this transfer has already been processed");
        try _usdc().transfer(requestor, amountRequested) {
            transfers_processed[transferUuid] = true;
            if (emitDepositedEvent) {
                emit Withdrawn(address(this), requestor, amountRequested, transferUuid);
            }
        } catch {
            revert("SettlementPool: Could not withdraw USDC.");
        }
    }

    function depositUSDCNoEvent(
        address sender,
        uint256 amount,
        uint128 transferUuid
    ) external nonReentrant onlyOracle {
        _depositUSDCOnBehalf(
            sender,
            amount,
            transferUuid,
            false /* emitDepositedEvent */
        );
    }

    function withdrawUSDCNoEvent(
        address requestor,
        uint256 amountRequested,
        uint128 transferUuid
    ) external nonReentrant onlyOracle {
        _withdrawUSDCOnBehalf(
            requestor,
            amountRequested,
            transferUuid,
            false /* emit_event */
        );
    }

    function withdrawUSDC(
        address requestor,
        uint256 amountRequested,
        uint128 transferUuid
    ) external nonReentrant onlyOracle {
        _withdrawUSDCOnBehalf(
            requestor,
            amountRequested,
            transferUuid,
            true /* emit_event */
        );
    }

    function addOtherParty(address otherAddress) external nonReentrant onlyOracle {
        require(
            otherAddresses[otherAddress] == false,
            "SettlementPool: the given address is already a party in the pool"
        );
        otherAddresses[otherAddress] = true;
        emit OtherPartyAdded(address(this), otherAddress);
    }
}
