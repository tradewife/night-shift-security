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