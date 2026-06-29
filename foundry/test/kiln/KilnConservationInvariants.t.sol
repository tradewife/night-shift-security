// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {HarnessBase} from "./HarnessBase.t.sol";
import {MockConnector} from "../../src/kiln/MockConnector.sol";
import {Vault} from "../../src/kiln/Vault.sol";

/// @notice Conservation + reward-fee accounting invariants.
contract KilnConservationInvariants is HarnessBase {
    function setUp() public override {
        super.setUp();
    }

    function test_conservation_singleDeposit_totalAssetsMatchesConnector() public {
        mockGoodConnector.setYield(100_000_000);
        assertEq(mockGoodConnector.totalAssets(IERC20(address(usdc))), 100_000_000);
        assertEq(vault.totalAssets(), 100_000_000, "vault delegates totalAssets to connector");
    }

    function test_shareInflation_firstDeposit() public {
        mintAndApprove(alice, 1_000_000_000);

        vm.prank(alice);
        uint256 shares = vault.deposit(100_000_000, alice);

        // With offset=0, fee=0:  shares = assets = 100_000_000
        assertEq(shares, 100_000_000);
        assertEq(vault.balanceOf(alice), shares);
        assertEq(vault.totalSupply(), shares);
    }

    function test_accruedRewardFeeCountsWithConnectorYield() public {
        // 1) Set reward fee before any deposit (doesn't affect supply=0 state)
        vm.prank(admin);
        vault.setRewardFee(3_500_000); // 3.5%

        // 2) Alice deposits first with totalAssets=0. supply=0, total=0.
        //    _convertToShares: assets * (0+1) / (0+1) = assets. Shares = assets.
        mintAndApprove(alice, 1_000_000_000);
        vm.prank(alice);
        uint256 shares = vault.deposit(50_000_000, alice);
        assertEq(shares, 50_000_000);

        // 3) Now seed yield. lastTotalAssets = 50M, totalAssets = 50M (still).
        //    No reward accrual yet because no user action triggered _accrueRewardFee.
        mockGoodConnector.setYield(100_000_000);

        // 4) Bob deposit triggers _accrueRewardFee: delta = 100M - 50M = 50M
        //    feeAmount = 50M * 3.5M / (100 * 1M) = 1.75M
        //    rewardShares = 1.75M * (50M+1) / (100M - 1.75M + 1) ≈ 892_857
        //    These are MINTED to address(this) and added to _collectableRewardFeesShares.
        //    Bob's deposit preview uses supply=50M+892_857, total=100M.
        //    _convertToShares: 10_000 * (50M+892_857+1) / (100M+1) ≈ ~5_089 → positive.
        mintAndApprove(bob, 1_000_000_000);
        vm.prank(bob);
        uint256 bobShares = vault.deposit(10_000, bob);
        assertGt(bobShares, 0, "bob gets positive shares");

        uint256 cr = vault.collectableRewardFees();
        emit log_named_uint("collectableRewardFees()", cr);

        // Reward fee should be meaningful (not zero) because shares were minted
        assertGt(cr, 1_000_000);

        // 6) Collect; supply must decrease
        uint256 supplyBefore = vault.totalSupply();
        vm.prank(admin);
        vault.collectRewardFees();
        uint256 supplyAfter = vault.totalSupply();
        emit log_named_uint("supplyBefore", supplyBefore);
        emit log_named_uint("supplyAfter", supplyAfter);

        assertLt(supplyAfter, supplyBefore, "supply decreased after collect");
    }
}
