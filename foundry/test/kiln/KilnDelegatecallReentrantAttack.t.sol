// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {HarnessBase} from "./HarnessBase.t.sol";
import {ReentrantConnector} from "../../src/kiln/ReentrantConnector.sol";

/// @notice Strategy 003 — Reentry via connector during deposit.
///         Vault.deposit() ends with `functionDelegateCall(IConnector.deposit,
///         (asset, amount))` — the connector's `deposit` runs in Vault's context.
///         A malicious connector can `vault.transfer()` etc. on the Vault in
///         that context, because msg.sender == address(this) == vault.
///         The Vault's transfer() does NOT use nonReentrant, so this reentry
///         is *only* stopped by what the *function checks at entry*. Transfer
///         has `_msgSender() notBlocked`, `to notBlocked`, but no auth — anyone
///         can transfer their own shares.  Hence the connector can't move OTHER
///         users' funds, but it CAN manipulate Vault storage during the
///         deposit's frame.
///
///         The most concerning variant: reentry to `_setOffset` or to
///         `_setConnectorRegistry` etc.  But those are internal.  Instead it
///         can call public functions like `pauseDeposit()` if it inherits the
///         admin role — which is a *vault-internal* role — *while* running in
///         the vault's context; but the `msg.sender` is the vault, and the
///         vault does not hold a role on itself (until admin grants one). So
///         this reentry is mostly inert.
///
///         What is NOT inert: reentry can call any external function via
///         `address(vault).call(...)` and pass arbitrary calldata — including
///         calls back into the *original user* entry-point.  Since the
///         connector could *also* dispatch to a malicious recipient, this
///         represents a partial-control path.
contract KilnDelegatecallReentrantAttack is HarnessBase {
    ReentrantConnector reentrantConnector;

    function setUp() public override {
        super.setUp();
        reentrantConnector = new ReentrantConnector(address(vault));
    }

    function test_reentrancyDuringDepositDoesNotImmediatelyRevert() public {
        vm.prank(admin);
        registry.update(CONNECTOR_NAME, address(reentrantConnector));

        reentrantConnector.setReenter(true);

        mintAndApprove(alice, 1_000_000_000);

        // alice deposit
        vm.prank(alice);
        uint256 shares = vault.deposit(50_000_000, alice);

        emit log_named_uint("shares returned", shares);
        assertGt(shares, 0);
    }

    function test_reentrancy_canCallPublicViewFunctions() public {
        vm.prank(admin);
        registry.update(CONNECTOR_NAME, address(reentrantConnector));

        reentrantConnector.setReenter(true);

        mintAndApprove(alice, 1_000_000_000);

        vm.prank(alice);
        vault.deposit(50_000_000, alice);

        // The Vault proxy may now have weird state.
        uint256 totalAssetsPost = vault.totalAssets();
        emit log_named_uint("vault.totalAssets() post-deposit", totalAssetsPost);

        // 50_000_000 = 5e7. Vault.totalAssets = .balanceOf(vault) at this point +
        // amount in connector. We don't assert super tightly — just instrument.
    }
}
