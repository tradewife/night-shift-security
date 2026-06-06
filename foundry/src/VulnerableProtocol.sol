// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title VulnerableProtocol — minimal harness mirroring Python mock ContractState
/// @notice Intentionally vulnerable contracts for Night Shift Security Foundry tests
contract VulnerableGovernance {
    uint256 public treasuryBalance;
    uint256 public totalVotingPower;
    uint256 public proposalThresholdPct;
    uint256 public timelockHours;
    uint256 public executionDelayHours;
    bool public flashLoanAvailable;

    constructor(
        uint256 _treasury,
        uint256 _totalVoting,
        uint256 _thresholdPct,
        uint256 _timelockHours,
        uint256 _executionDelayHours,
        bool _flashLoan
    ) {
        treasuryBalance = _treasury;
        totalVotingPower = _totalVoting;
        proposalThresholdPct = _thresholdPct;
        timelockHours = _timelockHours;
        executionDelayHours = _executionDelayHours;
        flashLoanAvailable = _flashLoan;
    }

    function attemptGovernanceCapture(
        uint256 votingPowerPct,
        bool useFlashLoan,
        bool bypassTimelock
    ) external returns (bool success, uint256 impact) {
        uint256 effectiveVoting = votingPowerPct;
        if (useFlashLoan && flashLoanAvailable) {
            effectiveVoting = votingPowerPct + 30;
            if (effectiveVoting > 100) effectiveVoting = 100;
        }

        uint256 votesNeeded = (totalVotingPower * proposalThresholdPct) / 100;
        uint256 attackerPower = (totalVotingPower * effectiveVoting) / 100;
        bool hasVotes = attackerPower >= votesNeeded;

        bool weakWindow = timelockHours < 48 || executionDelayHours < 1 || bypassTimelock;
        success = hasVotes && weakWindow && treasuryBalance > 0;

        if (success) {
            impact = treasuryBalance;
            treasuryBalance = 0;
        }
    }
}

contract VulnerableTreasury {
    uint256 public treasuryBalance;
    bool public adminCompromised;
    uint256 public withdrawalLimit;
    uint256 public multisigThreshold;

    constructor(uint256 _treasury, bool _adminCompromised, uint256 _limit, uint256 _multisig) {
        treasuryBalance = _treasury;
        adminCompromised = _adminCompromised;
        withdrawalLimit = _limit;
        multisigThreshold = _multisig;
    }

    function attemptDrain(
        uint256 withdrawalPct,
        bool useCompromisedAdmin,
        bool bypassMultisig
    ) external returns (bool success, uint256 impact) {
        bool hasAccess = (useCompromisedAdmin && adminCompromised)
            || (bypassMultisig && multisigThreshold <= 1);

        uint256 drainAmount = (treasuryBalance * withdrawalPct) / 100;
        bool withinLimit = withdrawalLimit == 0 || drainAmount <= withdrawalLimit || bypassMultisig;

        success = hasAccess && withinLimit && drainAmount > 0;
        if (success) {
            impact = drainAmount;
            treasuryBalance -= drainAmount;
        }
    }
}

contract VulnerableVault {
    uint256 public balance;
    bool public reentrancyGuard;
    bool public externalCallBeforeUpdate;
    bool public callbackEnabled;

    constructor(uint256 _balance, bool _guard, bool _ceiViolation, bool _callback) {
        balance = _balance;
        reentrancyGuard = _guard;
        externalCallBeforeUpdate = _ceiViolation;
        callbackEnabled = _callback;
    }

    function attemptReentrancy(uint256 depth) external returns (bool success, uint256 impact) {
        bool vulnerable = !reentrancyGuard || externalCallBeforeUpdate;
        success = vulnerable && callbackEnabled && depth >= 2 && balance > 0;
        if (success) {
            impact = (balance * depth * 80) / (depth * 100);
            if (impact > balance) impact = balance;
            balance -= impact;
        }
    }
}

contract VulnerableComposability {
    uint256 public treasuryBalance;
    uint256 public collateralLiquidity;
    uint256 public sharedLiquidity;
    uint256 public dependencyCount;
    bool public crossProtocolEnabled;
    bool public callbackEnabled;

    constructor(
        uint256 _treasury,
        uint256 _collateral,
        uint256 _shared,
        uint256 _deps,
        bool _cross,
        bool _callback
    ) {
        treasuryBalance = _treasury;
        collateralLiquidity = _collateral;
        sharedLiquidity = _shared;
        dependencyCount = _deps;
        crossProtocolEnabled = _cross;
        callbackEnabled = _callback;
    }

    function attemptComposability(
        uint256 hops,
        uint256 leverageMultiplier,
        bool useCallbackChain
    ) external returns (bool success, uint256 impact) {
        bool hasComposability = crossProtocolEnabled && sharedLiquidity > 0;
        bool callbackViable = useCallbackChain && callbackEnabled;
        bool collateralWeak = dependencyCount >= 2;

        uint256 inflated = (collateralLiquidity * leverageMultiplier) / 1e18;
        uint256 borrowCapacity = inflated < treasuryBalance / 2 ? inflated : treasuryBalance / 2;

        success = hasComposability
            && collateralWeak
            && hops >= 2
            && (callbackViable || !useCallbackChain)
            && borrowCapacity > 100_000;

        if (success) {
            impact = (borrowCapacity * 60) / 100;
            if (impact > treasuryBalance) impact = treasuryBalance;
            treasuryBalance -= impact;
        }
    }
}

contract VulnerableUpgradeable {
    uint256 public treasuryBalance;
    bool public upgradeableProxy;
    bool public adminCompromised;
    bool public proxyAdminUnprotected;
    bool public proxyInitialized;
    bool public storageCollisionRisk;

    constructor(
        uint256 _treasury,
        bool _proxy,
        bool _admin,
        bool _unprotected,
        bool _initialized,
        bool _collision
    ) {
        treasuryBalance = _treasury;
        upgradeableProxy = _proxy;
        adminCompromised = _admin;
        proxyAdminUnprotected = _unprotected;
        proxyInitialized = _initialized;
        storageCollisionRisk = _collision;
    }

    function attemptUpgrade(
        string memory method,
        bool storageCollision,
        bool skipInitializer
    ) external returns (bool success, uint256 impact) {
        bool canUpgrade = false;
        if (keccak256(bytes(method)) == keccak256(bytes("direct_admin"))) {
            canUpgrade = upgradeableProxy && (adminCompromised || proxyAdminUnprotected);
        } else if (keccak256(bytes(method)) == keccak256(bytes("storage_collision"))) {
            canUpgrade = upgradeableProxy && storageCollision && storageCollisionRisk;
        } else if (keccak256(bytes(method)) == keccak256(bytes("uninitialized_proxy"))) {
            canUpgrade = upgradeableProxy && skipInitializer && !proxyInitialized;
        }

        success = canUpgrade && treasuryBalance > 0;
        if (success) {
            impact = treasuryBalance;
            treasuryBalance = 0;
        }
    }
}

contract VulnerableAccessControl {
    uint256 public treasuryBalance;
    bool public privilegedFunctionExposed;
    bool public zeroRootVulnerable;
    bool public roleHierarchyBypass;
    bool public adminCompromised;

    constructor(
        uint256 _treasury,
        bool _exposed,
        bool _zeroRoot,
        bool _hierarchyBypass,
        bool _admin
    ) {
        treasuryBalance = _treasury;
        privilegedFunctionExposed = _exposed;
        zeroRootVulnerable = _zeroRoot;
        roleHierarchyBypass = _hierarchyBypass;
        adminCompromised = _admin;
    }

    function attemptEscalation(
        string memory targetRole,
        bool bypassRoleCheck,
        bool useZeroRoot
    ) external returns (bool success, uint256 impact) {
        bool roleExposed = privilegedFunctionExposed || bypassRoleCheck;
        bool zeroRootVuln = useZeroRoot && zeroRootVulnerable;
        bool hierarchyBypass = roleHierarchyBypass && bypassRoleCheck;

        bool canEscalate = (roleExposed && bypassRoleCheck)
            || zeroRootVuln
            || hierarchyBypass
            || (adminCompromised
                && (keccak256(bytes(targetRole)) == keccak256(bytes("owner"))
                    || keccak256(bytes(targetRole)) == keccak256(bytes("admin"))));

        success = canEscalate && treasuryBalance > 0;
        if (success) {
            if (keccak256(bytes(targetRole)) == keccak256(bytes("pauser"))) {
                impact = treasuryBalance / 2;
            } else {
                impact = treasuryBalance;
            }
            treasuryBalance -= impact;
        }
    }
}