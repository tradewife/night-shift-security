// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import "forge-std/Test.sol";

import {Vault} from "../../src/kiln/Vault.sol";
import {ConnectorRegistry} from "../../src/kiln/ConnectorRegistry.sol";
import {BlockList} from "../../src/kiln/BlockList.sol";
import {MockERC20} from "../../src/kiln/MockERC20.sol";
import {MockConnector} from "../../src/kiln/MockConnector.sol";
import {MaliciousConnector} from "../../src/kiln/MaliciousConnector.sol";
import {MockFeeDispatcher} from "../../src/kiln/MockFeeDispatcher.sol";
import {MockVaultFactory} from "../../src/kiln/MockVaultFactory.sol";
import {MockExternalAccessControl} from "../../src/kiln/MockExternalAccessControl.sol";
import {IFeeDispatcher} from "../../src/kiln/IFeeDispatcher.sol";

/// @title Kiln Harness Base
/// @notice Wires all harnesses needed for an OmniVault invariant campaign.
abstract contract HarnessBase is Test {
    // Actors
    address internal admin = makeAddr("admin");
    address internal alice = makeAddr("alice");
    address internal bob = makeAddr("bob");
    address internal attacker = makeAddr("attacker");

    // Underlying asset (USDC-like)
    MockERC20 internal usdc;
    MockERC20 internal rewardToken;

    // Fee dispatcher
    MockFeeDispatcher internal feeDispatcher;

    // Blocklist — a "no-op" implementation that allows everyone.
    BlockListMock internal blockListContract;

    // Connector registry 
    ConnectorRegistry internal registry;

    // ExternalAccessControl (mock for SPENDER_ROLE checks)
    MockExternalAccessControl internal externalAccess;

    // Factory
    MockVaultFactory internal factory;

    // Connector mocks
    MockConnector internal mockGoodConnector;
    MaliciousConnector internal maliciousConnector;
    bytes32 constant CONNECTOR_NAME = keccak256("MOCK_USDC_CONNECTOR");

    // Vault
    Vault internal vault;
    bytes32 constant SIMPLE_VAULT_STORAGE =
        0x6bb5a2a0ae924c2ea94f037035a09f65614421e2a7d96c9bcbd59acdd32e6000;

    function setUp() public virtual {
        usdc = new MockERC20("USD Coin", "USDC", 6);
        rewardToken = new MockERC20("Reward Token", "RWD", 18);
        feeDispatcher = new MockFeeDispatcher();
        externalAccess = new MockExternalAccessControl();

        blockListContract = new BlockListMock();
        factory = new MockVaultFactory();

        registry = new ConnectorRegistry(admin, admin, admin, admin, admin, 0);
        vm.startPrank(admin);
        registry.grantRole(registry.CONNECTOR_MANAGER_ROLE(), admin);
        registry.grantRole(registry.PAUSER_ROLE(), admin);
        registry.grantRole(registry.UNPAUSER_ROLE(), admin);
        registry.grantRole(registry.FREEZER_ROLE(), admin);
        vm.stopPrank();

        mockGoodConnector = new MockConnector();
        maliciousConnector = new MaliciousConnector();

        vm.prank(admin);
        registry.add(CONNECTOR_NAME, address(mockGoodConnector));

        vault = new Vault(address(externalAccess), address(factory));

        feeDispatcher.setAsset(address(usdc));
        vm.startPrank(address(factory));
        vault.initialize(
            Vault.InitializationParams({
                asset_: IERC20(address(usdc)),
                name_: "Kiln Mock USDC",
                symbol_: "kmUSDC",
                transferable_: true,
                connectorRegistry_: registry,
                connectorName_: CONNECTOR_NAME,
                depositFee_: 0,
                rewardFee_: 0,
                initialDefaultAdmin_: admin,
                initialFeeManager_: admin,
                initialSanctionsManager_: admin,
                initialClaimManager_: admin,
                initialPauser_: admin,
                initialUnpauser_: admin,
                initialDelay_: 0,
                offset_: 0,
                minTotalSupply_: 0
            }),
            Vault.UpgradeParams({
                recipients_: _emptyRecipients(),
                feeDispatcher_: address(feeDispatcher),
                additionalRewardsStrategy_: Vault.AdditionalRewardsStrategy.None,
                blockList_: blockListContract,
                pendingDepositFee_: 0,
                pendingRewardFee_: 0,
                connectorRegistry_: registry,
                initialFeeCollector_: admin
            })
        );
        vm.stopPrank();
    }

    function _emptyRecipients() internal pure returns (IFeeDispatcher.FeeRecipient[] memory r) {
        r = new IFeeDispatcher.FeeRecipient[](0);
    }

    function mintAndApprove(address who, uint256 amount) internal {
        usdc.mint(who, amount);
        vm.prank(who);
        usdc.approve(address(vault), type(uint256).max);
    }
}

/// @notice Minimal BlockList that always returns `false` from isBlocked.
///         Used to substitute the upgradeable BlockList in tests where we
///         don't need real sanctions checks.
contract BlockListMock is BlockList {
    function isBlocked(address) public pure override returns (bool) {
        return false;
    }

    function isBlockedByInternalList(address) public pure override returns (bool) {
        return false;
    }

    function isSanctionedByUnderlyingList(address) public pure override returns (bool) {
        return false;
    }

    function name() public pure override returns (string memory) {
        return "Mock";
    }
}
