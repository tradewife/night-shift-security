// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";
import {HarnessBase} from "./HarnessBase.t.sol";
import {MaliciousConnector} from "../../src/kiln/MaliciousConnector.sol";
import {Vault} from "../../src/kiln/Vault.sol";

/// @notice Strategy 002 — Re-entrant `MaliciousConnector` to demonstrate that the
///         Vault's `functionDelegateCall` path is reachable from arbitrary external
///         connector code, AND the connector can hit Vault's public functions
///         from within the delegatecall frame (reentrancy via `msg.sender`).
///
///         The Vault.deposit() flow is:
///         1. Vault executes mint + ERC20 transferFrom + bookkeeping
///         2. Vault calls `functionDelegateCall(IConnector.deposit, ...)`
///         3. Connector runs in Vault's context. If connector has malicious logic
///            that calls back into the Vault (e.g. withdraw), Vault's
///            `nonReentrant` modifier will refuse — *that part is protected*.
///         4. But during step 3 the connector can also WRITE to Vault's storage
///            via its declared mapping slots — clobbering Vault's parent layouts.
///
///         This test asserts the surface (without attempting full endgame exploit)
///         and logs Vault layout findings.
contract KilnDelegatecallReentrant is HarnessBase {
    function test_delegatecall_context_logs() public {
        // Replace the connector with the malicious one
        vm.prank(admin);
        registry.update(CONNECTOR_NAME, address(maliciousConnector));

        // First we examine the Vault proxy's storage layout to identify which slots
        // are "owned" by Vault parent contracts.  Then we trigger a benign deposit
        // and observe what the malicious connector caused.
        maliciousConnector.setHijack(address(0), 0);

        mintAndApprove(alice, 1_000_000_000);
        vm.prank(alice);
        uint256 shares = vault.deposit(50_000_000, alice);

        // Snapshot the Vault's *balanceOf(this)* (post-deposit) which now equals
        // assets in transit (50_000_000 USDC units).
        uint256 balAfter = usdc.balanceOf(address(vault));
        emit log_named_uint("Vault USDC balance post-deposit", balAfter);

        // Inspect the storage layout around the VaultStorage struct:
        // Slot 0x6bb5a2... (VaultStorage):
        //     0x00..0x14  IConnectorRegistry _connectorRegistry (20 bytes)
        //     0x14..0x24  bytes32 _connectorName
        //     0x24..0x44  uint256 _depositFee
        //     ... etc.
        // Reading those via vm.load gives a snapshot of the post-attack state.
        bytes32 vstruct = vm.load(address(vault), SIMPLE_VAULT_STORAGE);
        emit log_named_bytes32("VaultStorage[0]", vstruct);

        // Parse out the connectorRegistry address (low 20 bytes)
        address regAddrStored;
        assembly {
            regAddrStored := and(vstruct, 0x000000000000000000000000ffffffffffffffffffffffffffffffffffffffff)
        }
        emit log_named_address("VaultStorage._connectorRegistry (slot 0)", regAddrStored);

        // Assert it's still the original registry
        assertEq(regAddrStored, address(registry), "connector registry unchanged by benign flow");

        // The key open question:
        //   Does setLastTotalAssets = totalAssets() during the deposit write to the
        //   VaultStorage struct's slot, possibly at collision-boundary with adjacent
        //   helpers?  The struct is laid out in order: registry(160) name(256)
        //   depositFee(256) rewardFee(256) lastTotalAssets(256) ... collides at
        //   storage[2] = depositFee (256-aligned).  Two adjacent 256-bit slots per
        //   uint256 field give NO collision with the 160-bit _connectorRegistry.
        //
        // But the malicious connector writes to its own declared mapping slots. Those
        // slots, when laid out linearly inside the Vault proxy storage, are computed
        // from the slot indices asserted by the **connector source**.  If the
        // connector declares mapping at declared-index-0, it writes to slot 0 (the
        // 160-bit _connectorRegistry field).  If declared after an immutable, etc.

        // For visualization, also peek at slot 0 (where Vault stores nothing useful
        // except low-level bytes from inherited Initializer).
        bytes32 slot0 = vm.load(address(vault), bytes32(uint256(0)));
        emit log_named_bytes32("Vault storage slot 0", slot0);

        assertGt(shares, 0);
    }

    function test_VaultUpgradeableBeacon_storage_layout() public {
        // Inspect the beacon's storage layout. It uses OZ's transparent beacon:
        //   - slot 0  : _implementation (the Vault impl address)
        //   - slot 1  : pauseTimestamp (uint88)
        //   - slot 2  : frozen (bool)
        //   - other slot for AccessControlDefaultAdminRules: private fields packed at low slots.
        //
        // This is sanity for our understanding.
        bytes32 bslot0 = vm.load(address(factory /* factory is same addr */), bytes32(uint256(0)));
        // factory is unrelated — better: load a member of our registry (which uses
        // AccessControl storage layout we DO care about).
        bytes32 rslot0 = vm.load(address(registry), bytes32(uint256(0)));
        emit log_named_bytes32("Registry storage slot 0", rslot0);
        bslot0; // silence unused
    }

    function test_hijack_clobbers_vault_low_slots() public {
        // Replace the connector with the malicious one
        vm.prank(admin);
        registry.update(CONNECTOR_NAME, address(maliciousConnector));

        // The malicious connector's first declared non-mapping storage is
        // `hijackTarget` (slot 0). Setting it BEFORE the deposit means the
        // malicious connector's `deposit()` is invoked via delegatecall and
        // reflects the slot 0 from the Vault's storage context.
        maliciousConnector.setHijack(address(0), 0);
        maliciousConnector.setTotalAssetsLock(1);

        mintAndApprove(alice, 1_000_000_000);
        vm.prank(alice);
        uint256 shares = vault.deposit(50_000_000, alice);

        bytes32 s0 = vm.load(address(vault), bytes32(uint256(0)));
        emit log_named_bytes32("Vault slot 0 post-deposit", s0);
        // Slot 0 should reflect the malicious connector's `hijackTarget` since
        // it occupies the connector's first non-mapping slot. The malicious
        // code ran via delegatecall, writing to the Vault proxy's storage at
        // slot 0.
        // For `setHijack(0, 0)`, slot 0 of vault = 0.
        assertEq(uint256(s0), 0);
        shares; // silence unused
    }
}
