// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IFeeDispatcher} from "./IFeeDispatcher.sol";
import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";

/// @notice Minimal in-process FeeDispatcher mock
///         Tracks pending deposit + reward fees per asset, splits to recipients
///         on `dispatchFees`. Implementation is intentionally simple so invariant
///         tests can exercise Vault accounting against predictable fee splits.
contract MockFeeDispatcher is IFeeDispatcher {
    mapping(IERC20 => uint256) public pendingDepositFeeOf;
    mapping(IERC20 => uint256) public pendingRewardFeeOf;
    address public asset;
    FeeRecipient[] internal _recipients;

    uint256 public totalDispatched;
    address public lastDispatcher;

    constructor() {}

    function seedRecipients(FeeRecipient[] memory recipients_, uint8) external {
        delete _recipients;
        for (uint256 i = 0; i < recipients_.length; i++) {
            _recipients.push(recipients_[i]);
        }
    }

    function dispatchFees(IERC20 asset_, uint8) external override {
        lastDispatcher = msg.sender;
        uint256 total = pendingDepositFeeOf[asset_] + pendingRewardFeeOf[asset_];
        if (total == 0) return;
        if (asset_.balanceOf(address(this)) >= total) {
            asset_.transfer(msg.sender, total);
        }
        totalDispatched += total;
        pendingDepositFeeOf[asset_] = 0;
        pendingRewardFeeOf[asset_] = 0;
    }

    function pendingDepositFee() external view override returns (uint256) {
        return pendingDepositFeeOf[IERC20(asset)];
    }

    function pendingRewardFee() external view override returns (uint256) {
        return pendingRewardFeeOf[IERC20(asset)];
    }

    function feeRecipients() external view override returns (FeeRecipient[] memory) {
        return _recipients;
    }

    function feeRecipient(address recipient) external view override returns (FeeRecipient memory) {
        FeeRecipient[] memory r = _recipients;
        for (uint256 i = 0; i < r.length; i++) {
            if (r[i].recipient == recipient) return r[i];
        }
        // sentinel: empty recipient
        return FeeRecipient({recipient: address(0), depositFeeSplit: 0, rewardFeeSplit: 0});
    }

    function feeRecipientAt(uint256 index) external view override returns (FeeRecipient memory) {
        return _recipients[index];
    }

    function setFeeRecipients(FeeRecipient[] memory recipients_, uint8 underlyingDecimal) external override {
        delete _recipients;
        for (uint256 i = 0; i < recipients_.length; i++) {
            _recipients.push(recipients_[i]);
        }
    }

    function incrementPendingRewardFee(uint256 amount) external override {
        pendingRewardFeeOf[IERC20(asset)] += amount;
    }

    function incrementPendingDepositFee(uint256 amount) external override {
        pendingDepositFeeOf[IERC20(asset)] += amount;
    }

    function setAsset(address a) external {
        asset = a;
    }
}
