// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "lib/openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";
import "src/variational/src/Oracle.sol";
import "src/variational/src/SettlementPool.sol";
import "src/variational/src/SettlementPoolFactory.sol";
import "src/variational/mocks/MockUSDC.sol";
import "lib/forge-std/src/Test.sol";

/// @notice Stateful invariant test for the batchDepositUSDCAtomic over-deposit bug.
///          With N items in the atomic batch, the creator's amount is deposited N times,
///          breaking per-account conservation.
contract VariationalBatchInvariant is Test {
    MockUSDC usdc;
    Oracle oracle;
    SettlementPool impl;
    SettlementPoolFactory factory;

    address payable admin =
        payable(address(uint160(uint256(keccak256(abi.encode("variational_admin"))))));
    address creator =
        payable(address(uint160(uint256(keccak256(abi.encode("variational_creator"))))));
    address other1 =
        payable(address(uint160(uint256(keccak256(abi.encode("variational_other1"))))));
    address other2 =
        payable(address(uint160(uint256(keccak256(abi.encode("variational_other2"))))));
    address provider1 =
        payable(address(uint160(uint256(keccak256(abi.encode("variational_provider"))))));

    uint128 POOL_UUID = 5;

    address public pool;
    uint256 public expectedCreatorDeposited;

    function setUp() public {
        // Admin is a fresh EOA
        vm.prank(admin);
        usdc = new MockUSDC();
        impl = new SettlementPool();
        factory = new SettlementPoolFactory(address(impl), address(usdc));
        oracle = new Oracle();
        oracle.setSettlementPoolFactory(address(factory));
        factory.setOracleAddress(address(oracle));
        oracle.addProvider(provider1);

        // Whitelist creator + 2 other parties
        address[] memory others = new address[](2);
        others[0] = other1;
        others[1] = other2;
        vm.prank(provider1);
        oracle.createPool(creator, others, POOL_UUID, 11, 1, address(0), 0);
        pool = oracle.getPool(POOL_UUID);

        // Pre-fund
        usdc.mint(creator, 1_000_000e6);
        usdc.mint(other1,  1_000_000e6);
        usdc.mint(other2,  1_000_000e6);

        vm.prank(creator);
        usdc.approve(pool, type(uint256).max);
        vm.prank(other1);
        usdc.approve(pool, type(uint256).max);
        vm.prank(other2);
        usdc.approve(pool, type(uint256).max);
        vm.prank(creator);
        usdc.approve(address(oracle), type(uint256).max);
    }

    /// @notice invariant: pool balance == sum of actual charges to each party
    function invariant_poolBalanceEqualsRecord() public {
        uint256 poolBal = usdc.balanceOf(pool);
        // Pool only receives USDC through the oracle-mediated flows; if no flow ran this turn
        // we expect poolBal to grow only by legitimate deposit events.
        // No assertion here; this acts as a hook.
    }

    /// @notice action: 2-item batch atomic deposit
    function action_batchAtomic2() public {
        uint256 cp = usdc.balanceOf(creator);
        uint256 op1 = usdc.balanceOf(other1);
        uint256 op2 = usdc.balanceOf(other2);
        uint256 pb = usdc.balanceOf(pool);
        if (cp < 5e6 || op1 < 10e6 || op2 < 20e6) return;

        SettlementPools.AtomicDepositBatchItem[] memory items = new SettlementPools.AtomicDepositBatchItem[](2);
        items[0] = SettlementPools.AtomicDepositBatchItem({
            otherPartyAddress: other1,
            otherPartyAmountRequested: 10e6,
            rfqUuid: 11,
            parentQuoteUuid: uint128(uint256(keccak256(abi.encode("u", 0))))
        });
        items[1] = SettlementPools.AtomicDepositBatchItem({
            otherPartyAddress: other2,
            otherPartyAmountRequested: 20e6,
            rfqUuid: 11,
            parentQuoteUuid: uint128(uint256(keccak256(abi.encode("u", 1))))
        });

        vm.prank(provider1);
        oracle.batchAtomicDeposit(POOL_UUID, creator, 5e6, items);

        // BUG-EXPECTED: pool does 5+5+10+20 = 40e6 instead of 5+10+20 = 35e6
        assertEq(usdc.balanceOf(pool), pb + 40e6, "BUG: creator over-deposit N=2");
    }
}
