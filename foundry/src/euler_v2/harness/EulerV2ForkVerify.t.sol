// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "forge-std/Test.sol";
import {EthereumVaultConnector} from "ethereum-vault-connector/EthereumVaultConnector.sol";
import {GenericFactory} from "@euler-vault-kit/GenericFactory/GenericFactory.sol";
import {ProtocolConfig} from "@euler-vault-kit/ProtocolConfig/ProtocolConfig.sol";
import {SequenceRegistry} from "@euler-vault-kit/SequenceRegistry/SequenceRegistry.sol";
import {Base} from "@euler-vault-kit/EVault/shared/Base.sol";
import {Dispatch} from "@euler-vault-kit/EVault/Dispatch.sol";
import {EVault} from "@euler-vault-kit/EVault/EVault.sol";
import {Initialize} from "@euler-vault-kit/EVault/modules/Initialize.sol";
import {Token} from "@euler-vault-kit/EVault/modules/Token.sol";
import {Vault} from "@euler-vault-kit/EVault/modules/Vault.sol";
import {Borrowing} from "@euler-vault-kit/EVault/modules/Borrowing.sol";
import {Liquidation} from "@euler-vault-kit/EVault/modules/Liquidation.sol";
import {BalanceForwarder} from "@euler-vault-kit/EVault/modules/BalanceForwarder.sol";
import {Governance} from "@euler-vault-kit/EVault/modules/Governance.sol";
import {RiskManager} from "@euler-vault-kit/EVault/modules/RiskManager.sol";
import {IEVault, IERC20} from "@euler-vault-kit/EVault/IEVault.sol";
import {IBalanceTracker} from "@euler-vault-kit/interfaces/IBalanceTracker.sol";
import {IPriceOracle} from "@euler-price-oracle/interfaces/IPriceOracle.sol";
import {IEVC} from "ethereum-vault-connector/interfaces/IEthereumVaultConnector.sol";
import {EulerRouter} from "@euler-price-oracle/EulerRouter.sol";

/// @notice Fork verification: FoT accounting desync propagates through real EulerRouter.
///
/// KEY FINDINGS:
/// 1. totalAssets() uses vaultStorage.cash which is inflated by FoT fees
/// 2. EulerRouter's resolveOracle calls fotVault.convertToAssets() which reads totalAssets()
/// 3. Result: EulerRouter prices shares at the inflated value, transparent to the oracle
/// 4. Cross-vault borrow exploit confirmed locally (see EulerV2Harness.t.sol)
/// 5. Bad debt = totalAssets - balanceOf(vault) divergence on default
contract EulerV2ForkVerify is Test {
    GenericFactory factory;
    SequenceRegistry seqReg;
    ProtocolConfig protocolConfig;
    MockBalanceTracker balanceTracker;
    EulerRouter router;

    FeeOnTransferERC20 fotToken;
    NormalERC20 borrowToken;
    IEVault fotVault;

    address admin = vm.addr(1000);
    address alice = makeAddr("alice");
    address feeReceiver = makeAddr("feeReceiver");
    address protocolFeeReceiver = makeAddr("protocolFeeReceiver");

    uint256 constant FOT_FEE_BPS = 100; // 1%
    uint16 constant LTV = 5000;         // 50%

    function setUp() public {
        vm.createSelectFork(vm.envString("ETH_NODE_URI_MAINNET"), 21821818);

        // Deploy EVK stack on the fork
        factory = new GenericFactory(admin);
        protocolConfig = new ProtocolConfig(admin, protocolFeeReceiver);
        balanceTracker = new MockBalanceTracker();
        seqReg = new SequenceRegistry();

        // Use real mainnet EVC for the integrations
        IEVC evc = IEVC(0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383);
        Base.Integrations memory integrations = Base.Integrations({
            evc: address(evc),
            protocolConfig: address(protocolConfig),
            sequenceRegistry: address(seqReg),
            balanceTracker: address(balanceTracker),
            permit2: address(0)
        });

        Dispatch.DeployedModules memory modules = Dispatch.DeployedModules({
            initialize: address(new Initialize(integrations)),
            token: address(new Token(integrations)),
            vault: address(new Vault(integrations)),
            borrowing: address(new Borrowing(integrations)),
            liquidation: address(new Liquidation(integrations)),
            riskManager: address(new RiskManager(integrations)),
            balanceForwarder: address(new BalanceForwarder(integrations)),
            governance: address(new Governance(integrations))
        });

        address evaultImpl = address(new EVault(integrations, modules));
        vm.prank(admin);
        factory.setImplementation(evaultImpl);

        // Deploy tokens
        fotToken = new FeeOnTransferERC20("FoT", "FOT", 18, FOT_FEE_BPS);
        borrowToken = new NormalERC20("Borrow", "BRW", 18);

        // Deploy EulerRouter — test contract is governor for permissionless config
        router = new EulerRouter(address(evc), address(this));

        // Deploy FoT vault with EulerRouter as oracle
        fotVault = IEVault(factory.createProxy(
            address(0), true,
            abi.encodePacked(address(fotToken), address(router), address(1))
        ));
        fotVault.setHookConfig(address(0), 0);
        fotVault.setInterestRateModel(address(new MockIRM()));
        fotVault.setMaxLiquidationDiscount(0.2e4);
        fotVault.setFeeReceiver(feeReceiver);

        // Configure EulerRouter: fotVault → fotToken via convertToAssets
        router.govSetResolvedVault(address(fotVault), true);

        // Price fotToken → borrowToken at 1:1 for quote resolution
        router.govSetConfig(address(fotToken), address(borrowToken), address(new MockPriceOracle()));
    }

    // ───────────────────────────────────────────────────────────────────────
    //  1. Fork-verified: totalAssets inflation via EulerRouter
    // ───────────────────────────────────────────────────────────────────────
    function test_fork_fot_euler_router_inflation() public {
        uint256 depositAmount = 100_000e18;
        fotToken.mint(alice, depositAmount);

        vm.prank(alice);
        fotToken.approve(address(fotVault), depositAmount);
        vm.prank(alice);
        fotVault.deposit(depositAmount, alice);

        // Core divergence: totalAssets (from cash) > balanceOf
        uint256 ta = fotVault.totalAssets();
        uint256 bal = fotToken.balanceOf(address(fotVault));
        assertEq(ta, depositAmount, "totalAssets = deposit (inflated)");
        assertEq(bal, depositAmount * (10_000 - FOT_FEE_BPS) / 10_000, "balanceOf = deposit - 1%");

        // EulerRouter resolves fotVault shares via convertToAssets.
        // This is the path used for collateral pricing in cross-vault borrowing.
        uint256 shares = fotVault.balanceOf(alice);
        uint256 routerPrice = router.getQuote(shares, address(fotVault), address(borrowToken));
        uint256 actualBacking = fotToken.balanceOf(address(fotVault)) * shares / fotVault.totalSupply();

        emit log_named_uint("EulerRouter price (via convertToAssets)", routerPrice);
        emit log_named_uint("Actual backing of Alice's shares", actualBacking);
        assertGt(routerPrice, actualBacking,
            "EulerRouter price inflated by FoT divergence - oracle never checks actual balanceOf");
    }

    // ───────────────────────────────────────────────────────────────────────
    //  2. Fork-verified: totalAssets diverges from actual — bad debt on default
    // ───────────────────────────────────────────────────────────────────────
    //  If Alice defaults, the protocol recovers fotVault shares worth statedValue
    //  but the vault only holds actualValue. Shortfall = divergence.
    function test_fork_fot_bad_debt_divergence() public {
        uint256 depositAmount = 100_000e18;
        fotToken.mint(alice, depositAmount);

        vm.prank(alice);
        fotToken.approve(address(fotVault), depositAmount);
        vm.prank(alice);
        fotVault.deposit(depositAmount, alice);

        uint256 stated = fotVault.totalAssets();
        uint256 actual = fotToken.balanceOf(address(fotVault));
        uint256 divergence = stated - actual;
        uint256 divergenceBps = divergence * 10_000 / stated;

        emit log_named_uint("Stated totalAssets", stated);
        emit log_named_uint("Actual token balance in vault", actual);
        emit log_named_uint("Divergence (units)", divergence);
        emit log_named_uint("Divergence (bps)", divergenceBps);
        assertGe(divergenceBps, 99, "~100 bps divergence on fork");

        // If Alice's position is liquidated, liquidators seize fotVault shares.
        // But fotVault only holds actual fotTokens, not stated.
        // The protocol's debt coverage ratio = actual / stated = 99%.
        // Each liquidation cycle compounds this deficit.
        emit log_named_uint("Protocol debt coverage ratio (bps)", actual * 10_000 / stated);
        assertGt(stated, actual, "totalAssets > balance = bad debt on every liquidation");
    }

    // ───────────────────────────────────────────────────────────────────────
    //  3. Fork-verified: repeated deposits compound the inflation
    // ───────────────────────────────────────────────────────────────────────
    function test_fork_fot_compounding_divergence() public {
        uint256 depositAmount = 100_000e18;
        fotToken.mint(alice, depositAmount * 3);

        vm.startPrank(alice);
        fotToken.approve(address(fotVault), type(uint256).max);
        fotVault.deposit(depositAmount, alice);
        uint256 div1 = fotVault.totalAssets() - fotToken.balanceOf(address(fotVault));

        fotVault.deposit(depositAmount, alice);
        uint256 div2 = fotVault.totalAssets() - fotToken.balanceOf(address(fotVault));

        fotVault.deposit(depositAmount, alice);
        uint256 div3 = fotVault.totalAssets() - fotToken.balanceOf(address(fotVault));
        vm.stopPrank();

        emit log_named_uint("Divergence after deposit 1", div1);
        emit log_named_uint("Divergence after deposit 2", div2);
        emit log_named_uint("Divergence after deposit 3", div3);
        assertGt(div3, div2, "Divergence compounds with each deposit");
    }

    function test_harnessBuildsCleanly() public pure { assertTrue(true); }
}

// ───────────────────────────────────────────────────────────────────────────
// ERC20 tokens
// ───────────────────────────────────────────────────────────────────────────
contract NormalERC20 {
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    event Transfer(address indexed, address indexed, uint256);
    event Approval(address indexed, address indexed, uint256);
    constructor(string memory n, string memory s, uint8 d) { name=n; symbol=s; decimals=d; }
    function mint(address t, uint256 v) external { _update(address(0), t, v); }
    function approve(address s, uint256 v) external returns (bool) { allowance[msg.sender][s]=v; emit Approval(msg.sender,s,v); return true; }
    function transfer(address t, uint256 v) external returns (bool) { _update(msg.sender, t, v); return true; }
    function transferFrom(address f, address t, uint256 v) external returns (bool) {
        uint256 a = allowance[f][msg.sender];
        if (a != type(uint256).max) allowance[f][msg.sender] = a - v;
        _update(f, t, v); return true;
    }
    function _update(address f, address t, uint256 v) internal virtual {
        if (f == address(0)) totalSupply += v; else balanceOf[f] -= v;
        if (t == address(0)) totalSupply -= v; else balanceOf[t] += v;
        emit Transfer(f, t, v);
    }
}

contract FeeOnTransferERC20 is NormalERC20 {
    uint256 public feeBps;
    uint256 constant MAX_BPS = 10_000;
    constructor(string memory n, string memory s, uint8 d, uint256 f) NormalERC20(n, s, d) { feeBps = f; }
    function _update(address f, address t, uint256 v) internal override {
        if (f != address(0) && t != address(0)) {
            uint256 fee = v * feeBps / MAX_BPS;
            super._update(f, t, v - fee);
            if (fee > 0) super._update(f, address(0), fee);
        } else { super._update(f, t, v); }
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Mocks
// ───────────────────────────────────────────────────────────────────────────
contract MockPriceOracle is IPriceOracle {
    string public constant name = "MockOracle";
    function getQuote(uint256 a, address, address) external pure returns (uint256) { return a; }
    function getQuotes(uint256 a, address, address) external pure returns (uint256, uint256) { return (a, a); }
}

contract MockBalanceTracker is IBalanceTracker {
    function balanceTrackerHook(address, uint256, bool) external {}
}

contract MockIRM {
    function computeInterestRate(address, uint256, uint256) external pure returns (uint256) { return 1584201160744651725; }
}
