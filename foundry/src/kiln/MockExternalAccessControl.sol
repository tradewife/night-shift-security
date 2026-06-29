// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

/// @notice Mock ExternalAccessControl contract.
contract MockExternalAccessControl {
    mapping(bytes32 => mapping(address => bool)) public hasRole;
    mapping(address => bool) public allSpenders;

    function setRole(bytes32 role, address account, bool value) external {
        hasRole[role][account] = value;
    }

    function setSpenderRole(address account, bool value) external {
        bytes32 SPENDER = keccak256("SPENDER");
        hasRole[SPENDER][account] = value;
    }

    function hasRoleExternal(bytes32 role, address account) external view returns (bool) {
        return hasRole[role][account];
    }
}
