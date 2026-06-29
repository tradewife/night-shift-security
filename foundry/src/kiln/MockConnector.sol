// SPDX-License-Identifier: MIT
pragma solidity 0.8.22;

import {IConnector} from "./IConnector.sol";
import {IERC20} from "@openzeppelin/token/ERC20/IERC20.sol";

/// @notice Mock connector that simulates a yield sink.
///         Real connectors (Aave/Morpho/etc.) cross-call external protocols,
///         which has the natural side-effect of tracking deposits.  In tests
///         we want a deterministic ledger the harness can manipulate.  Because
///         `Vault._deposit/_withdraw` invokes us via DELEGATECALL, storage
///         writes in our `deposit` and `withdraw` go to the **Vault proxy's**
///         slots — not back to the connector.  Reading our own `assetDeposited`
///         mapping via `.call` from `totalAssets()` then sees the original
///         (untouched) connector storage — and the values are inconsistent.
///
///         To avoid that confusion in tests we keep this connector stateless
///         for deposit/withdraw (no storage writes inside the delegatecall),
///         and rely on test-set helpers (`setYield`, `_lastTotalSimulated`) to
///         seed the ledger the harness wants to assert against.
contract MockConnector is IConnector {
    uint256 public claimCount;
    uint256 public reinvestCount;

    uint256 public maxDep = type(uint256).max;
    uint256 public maxWd = type(uint256).max;

    /// Yield balance the connector pretends to hold.
    uint256 internal _yieldTotal;

    function totalAssets(IERC20) external view override returns (uint256) {
        return _yieldTotal;
    }

    function deposit(IERC20, uint256) external override {
        // No-op. The Vault already holds the asset; a real connector would
        // forward it to an external yield protocol.
    }

    function withdraw(IERC20, uint256) external override {
        // No-op. The Vault already holds the asset; a real connector would
        // pull it from an external yield protocol to the Vault.
    }

    function claim(IERC20, IERC20, bytes calldata) external override returns (uint256) {
        claimCount += 1;
        return 0;
    }

    function reinvest(IERC20, IERC20, bytes calldata) external override {
        reinvestCount += 1;
    }

    function maxDeposit(IERC20) external view override returns (uint256) {
        return maxDep;
    }

    function maxWithdraw(IERC20) external view override returns (uint256) {
        return maxWd;
    }

    /// Test hooks
    function setMax(uint256 maxDep_, uint256 maxWd_) external {
        maxDep = maxDep_;
        maxWd = maxWd_;
    }

    function setYield(uint256 newTotalAssets) external {
        _yieldTotal = newTotalAssets;
    }

    function seedRewards(IERC20, uint256 amount) external {
        // No-op: rewards strategy handled outside.
        amount; // silencer
    }
}
