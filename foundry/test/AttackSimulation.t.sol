// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/VulnerableProtocol.sol";

/// @title AttackSimulation — Foundry harness mirroring Python attack templates
contract AttackSimulationTest is Test {
    function _envUint(string memory key, uint256 defaultVal) internal view returns (uint256) {
        try vm.envUint(key) returns (uint256 val) {
            return val;
        } catch {
            return defaultVal;
        }
    }

    function _envBool(string memory key, bool defaultVal) internal view returns (bool) {
        try vm.envBool(key) returns (bool val) {
            return val;
        } catch {
            return defaultVal;
        }
    }

    function testGovernanceCapture() public {
        uint256 treasury = _envUint("TREASURY_BALANCE_USD", 182_000_000);
        uint256 votingPct = _envUint("VOTING_POWER_PCT", 67);
        bool useFlashLoan = _envBool("USE_FLASH_LOAN", true);
        bool bypassTimelock = _envBool("BYPASS_TIMELOCK", true);

        VulnerableGovernance gov = new VulnerableGovernance(
            treasury,
            100_000_000,
            50,
            0,
            0,
            true
        );

        (bool success, uint256 impact) = gov.attemptGovernanceCapture(
            votingPct,
            useFlashLoan,
            bypassTimelock
        );

        assertTrue(success, "governance capture should succeed");
        assertGt(impact, 0, "impact must be positive");
        console2.log("IMPACT_USD:%s", impact);
    }

    function testTreasuryDrain() public {
        uint256 treasury = _envUint("TREASURY_BALANCE_USD", 625_000_000);
        uint256 withdrawalPct = _envUint("WITHDRAWAL_PCT", 100);
        bool useAdmin = _envBool("USE_COMPROMISED_ADMIN", true);
        bool bypassMultisig = _envBool("BYPASS_MULTISIG", true);

        VulnerableTreasury vault = new VulnerableTreasury(treasury, true, 0, 1);

        (bool success, uint256 impact) = vault.attemptDrain(
            withdrawalPct,
            useAdmin,
            bypassMultisig
        );

        assertTrue(success, "treasury drain should succeed");
        assertGt(impact, 0, "impact must be positive");
        console2.log("IMPACT_USD:%s", impact);
    }

    function testFlashLoanOracle() public {
        // Foundry harness: flash loan oracle attacks validated via mock params
        // Full oracle manipulation requires fork — this test confirms template wiring
        uint256 loanAmount = _envUint("LOAN_AMOUNT_USD", 50_000_000);
        uint256 manipulationPct = _envUint("PRICE_MANIPULATION_PCT", 100);
        bool singleOracle = _envBool("USE_SINGLE_ORACLE", true);

        assertTrue(loanAmount > 0, "loan amount required");
        assertTrue(manipulationPct > 0, "manipulation required");
        assertTrue(singleOracle, "single oracle assumed");

        uint256 impact = (loanAmount * manipulationPct * 30) / 10000;
        assertGt(impact, 1_000_000, "impact should exceed threshold");
        console2.log("IMPACT_USD:%s", impact);
    }

    function testReentrancy() public {
        uint256 treasury = _envUint("TREASURY_BALANCE_USD", 197_000_000);
        uint256 depth = _envUint("RECURSION_DEPTH", 10);

        VulnerableVault vault = new VulnerableVault(treasury, false, true, true);

        (bool success, uint256 impact) = vault.attemptReentrancy(depth);

        assertTrue(success, "reentrancy should succeed");
        assertGt(impact, 0, "impact must be positive");
        console2.log("IMPACT_USD:%s", impact);
    }

    function testComposabilityRisk() public {
        uint256 treasury = _envUint("TREASURY_BALANCE_USD", 70_000_000);
        uint256 hops = _envUint("PROTOCOL_HOPS", 3);
        uint256 leverage = _envUint("LEVERAGE_MULTIPLIER", 5);
        bool useCallbacks = _envBool("USE_CALLBACK_CHAIN", true);

        VulnerableComposability protocol = new VulnerableComposability(
            treasury,
            200_000_000,
            500_000_000,
            4,
            true,
            true
        );

        (bool success, uint256 impact) = protocol.attemptComposability(hops, leverage * 1e18, useCallbacks);

        assertTrue(success, "composability attack should succeed");
        assertGt(impact, 0, "impact must be positive");
        console2.log("IMPACT_USD:%s", impact);
    }

    function testUpgradeabilityRisk() public {
        uint256 treasury = _envUint("TREASURY_BALANCE_USD", 6_000_000);
        string memory method = vm.envOr("UPGRADE_METHOD", string("storage_collision"));
        bool collision = _envBool("STORAGE_COLLISION", true);
        bool skipInit = _envBool("SKIP_INITIALIZER", false);

        VulnerableUpgradeable proxy = new VulnerableUpgradeable(
            treasury,
            true,
            false,
            false,
            true,
            true
        );

        (bool success, uint256 impact) = proxy.attemptUpgrade(method, collision, skipInit);

        assertTrue(success, "upgrade attack should succeed");
        assertGt(impact, 0, "impact must be positive");
        console2.log("IMPACT_USD:%s", impact);
    }

    function testAccessControlEscalation() public {
        uint256 treasury = _envUint("TREASURY_BALANCE_USD", 190_000_000);
        string memory targetRole = vm.envOr("TARGET_ROLE", string("admin"));
        bool bypassCheck = _envBool("BYPASS_ROLE_CHECK", true);
        bool useZeroRoot = _envBool("USE_ZERO_ROOT", true);

        VulnerableAccessControl protocol = new VulnerableAccessControl(
            treasury,
            true,
            true,
            true,
            false
        );

        (bool success, uint256 impact) = protocol.attemptEscalation(targetRole, bypassCheck, useZeroRoot);

        assertTrue(success, "access control escalation should succeed");
        assertGt(impact, 0, "impact must be positive");
        console2.log("IMPACT_USD:%s", impact);
    }
}