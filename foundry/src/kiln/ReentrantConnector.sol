// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {IConnector} from "../../src/kiln/IConnector.sol";
import {Vault} from "../../src/kiln/Vault.sol";

/// @notice Malicious connector that returns *control flow* back to the Vault
///         during the deposit delegatecall. We cannot reenter Vault.deposit
///         directly because of nonReentrant, but we *can* call back into
///         Vault's other public functions (transfer, etc.) which share the
///         delegatecall frame.
///
///         Specifically: during the deposit delegatecall, we call
///         vault.transfer(to, value) on the Vault's storage itself (because
///         the Vault's `transfer` actually moves CORRECT amounts; but the
///         effect of internal state manipulation during the receipt of the
///         transfer's `_msgSender()` (which is the original user) is what
///         matters).
///
///         Note: nonce/reentrancy protection via `nonReentrant` blocks
///         calling deposit twice.  But other Vault functions lack
///         nonReentrant.  The Vault's `transfer()` does NOT have
///         nonReentrant.  So during `functionDelegateCall(IConnector.deposit, ...)`
///         a malicious connector could call vault.transfer(...) — and that
///         would pass `_msgSender() == address(this)` (the Vault itself),
///         bypassing the `checkTransferability(notBlocked(_msgSender()))`
///         check (which is satisfied for self-transfers).
contract ReentrantConnector is IConnector {
    address public vault;
    bool public reenterOnDeposit;

    constructor(address vault_) {
        vault = vault_;
    }

    function totalAssets(IERC20) external pure override returns (uint256) {
        return 0;
    }

    function deposit(IERC20, uint256) external override {
        if (reenterOnDeposit) {
            // Try transferring part of our shares to self. Since we're running in
            // the Vault's delegatecall context, address(this) == vault.
            // Calling vault.transfer(...) from the vault's context is allowed
            // (msg.sender == address(this) in the vault's view), so checkTransferability
            // passes for self-targeting.  We pick a benign interaction here just to
            // prove the re-entry doesn't immediately revert.
            (bool ok, ) = vault.call(abi.encodeWithSignature("transfer(address,uint256)", address(this), 0));
            ok; // silencer
        }
    }

    function withdraw(IERC20, uint256) external pure override {
        // do nothing
    }

    function claim(IERC20, IERC20, bytes calldata) external pure override returns (uint256) {
        return 0;
    }

    function reinvest(IERC20, IERC20, bytes calldata) external pure override {}

    function maxDeposit(IERC20) external pure override returns (uint256) {
        return type(uint256).max;
    }

    function maxWithdraw(IERC20) external pure override returns (uint256) {
        return type(uint256).max;
    }

    function setReenter(bool flag) external {
        reenterOnDeposit = flag;
    }
}
