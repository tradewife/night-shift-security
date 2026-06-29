// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

/// @notice Mock Vault factory that simply acts as the onlyFactory() caller.
///         Use: from this factory's address call `vault.initialize(params, upParams)`
///         to satisfy the factory check (`msg.sender == vaultFactory`).
contract MockVaultFactory {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function _self() external view returns (address) {
        return address(this);
    }

    /**
     * @notice Helper to relay initialize() to a vault deployed with the factory as `vaultFactory`.
     * @param vault The vault to initialize.
     * @param initBytes ABI-encoded `(InitializationParams, UpgradeParams)`.
     */
    function callInitialize(address vault, bytes calldata initBytes) external {
        // solhint-disable-next-line avoid-low-level-calls
        (bool ok, bytes memory ret) = vault.call(initBytes);
        if (!ok) {
            // bubble up
            assembly {
                revert(add(ret, 0x20), mload(ret))
            }
        }
    }
}
