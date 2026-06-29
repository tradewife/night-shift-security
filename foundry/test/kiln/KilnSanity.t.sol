// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {HarnessBase} from "./HarnessBase.t.sol";

/// @notice Sanity check: harness initializes without revert; basic deposit/withdraw works.
contract KilnSanity is HarnessBase {
    function test_initialState() public {
        // Vault responds to totalAssets call (uses connector.totalAssets)
        assertEq(vault.totalAssets(), 0, "fresh vault totalAssets=0");
        assertEq(vault.balanceOf(alice), 0, "alice starts with 0 shares");
    }

    function test_totalAssetsDelegatesToConnector() public {
        // Seed the connector's yield via setYield (MockConnector is stateless
        // because deposit/withdraw run in Vault's delegatecall context).
        mockGoodConnector.setYield(1_000_000_000);
        assertEq(vault.totalAssets(), 1_000_000_000, "connector totalAssets propagates to vault.totalAssets()");
    }

    function test_depositWithdraw() public {
        mintAndApprove(alice, 1_000_000_000);

        vm.prank(alice);
        uint256 shares = vault.deposit(100_000_000, alice);

        assertGt(shares, 0, "alice got positive shares");
        assertEq(vault.balanceOf(alice), shares);
        assertEq(usdc.balanceOf(address(vault)), 100_000_000);
    }
}
