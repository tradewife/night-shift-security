// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "lib/openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";

/// @notice Minimal deterministic USDC for the Variational harness.
/// @dev Replicates the surface that SettlementPool / Oracle actually use:
///      transferFrom, transfer, allowance, balanceOf, and the ability to
///      intentionally fail transferFrom in adversarial scenarios.
contract MockUSDC is IERC20 {
    string public constant name = "MockUSDC";
    string public constant symbol = "USDC";
    uint8 public constant decimals = 6;

    uint256 public override totalSupply;
    mapping(address => uint256) public override balanceOf;
    mapping(address => mapping(address => uint256)) public override allowance;

    /// @dev Adversarial failure flag used by harness on a per-account basis.
    mapping(address => bool) public failTransferFrom;
    mapping(address => bool) public failTransfer;
    /// @dev Optional transfer-fee hook (basis points, 1bp = 0.01%)
    uint256 public transferFeeBps;
    /// @dev Hook-authoritative: if non-zero, transfer from sender deducts fee to feeSink.
    address public feeSink;

    function setFailTransferFrom(address who, bool v) external { failTransferFrom[who] = v; }
    function setFailTransfer(address who, bool v) external { failTransfer[who] = v; }
    function setTransferFeeBps(uint256 bps) external { transferFeeBps = bps; }
    function setFeeSink(address sink) external { feeSink = sink; }

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function burn(address from, uint256 amount) external {
        require(balanceOf[from] >= amount, "MockUSDC: burn > balance");
        balanceOf[from] -= amount;
        totalSupply -= amount;
        emit Transfer(from, address(0), amount);
    }

    function approve(address spender, uint256 amount) external override returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external override returns (bool) {
        return _transfer(msg.sender, to, amount);
    }

    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) {
            require(allowed >= amount, "MockUSDC: insufficient allowance");
            allowance[from][msg.sender] = allowed - amount;
        }
        return _transfer(from, to, amount);
    }

    function _transfer(address from, address to, uint256 amount) internal returns (bool) {
        require(balanceOf[from] >= amount, "MockUSDC: insufficient balance");
        if (failTransferFrom[from] || failTransfer[from]) return false;

        balanceOf[from] -= amount;

        uint256 fee = 0;
        if (transferFeeBps > 0 && feeSink != address(0)) {
            fee = (amount * transferFeeBps) / 10_000;
            balanceOf[feeSink] += fee;
            emit Transfer(from, feeSink, fee);
        }

        uint256 net = amount - fee;
        balanceOf[to] += net;
        emit Transfer(from, to, net);
        return true;
    }
}
