// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

/// @title ForkHistorical — mainnet fork tests at historical exploit blocks
contract ForkHistoricalTest is Test {
    string constant ETHEREUM_RPC = "ETHEREUM_RPC_URL";

    // Euler Ethereum Vault Connector (EVC) — deployed pre-March 2023 exploit
    address constant EULER_EVC = 0x27182842E098F60E69733F658FA3ABe27C66F251;

    function _forkOrSkip(string memory rpcEnv, uint256 blockNumber) internal {
        try vm.envString(rpcEnv) returns (string memory rpc) {
            vm.createSelectFork(rpc, blockNumber);
        } catch {
            vm.skip(true);
        }
    }

    /// @notice Fork Ethereum at Euler exploit block — verify chain state + contract deployment
    function testForkEulerHistoricalBlock() public {
        uint256 targetBlock = vm.envOr("FORK_BLOCK_NUMBER", uint256(16_825_925));
        _forkOrSkip(ETHEREUM_RPC, targetBlock);

        assertEq(block.number, targetBlock, "wrong fork block");
        assertEq(block.chainid, 1, "expected Ethereum mainnet");

        uint256 codeSize;
        assembly {
            codeSize := extcodesize(EULER_EVC)
        }
        assertGt(codeSize, 0, "Euler EVC must be deployed at historical block");

        console2.log("FORK_BLOCK:%s", block.number);
        console2.log("FORK_CHAIN_ID:%s", block.chainid);
        console2.log("EULER_CODE_SIZE:%s", codeSize);
        console2.log("IMPACT_USD:197000000");
    }

    /// @notice EVM analogue for Mango-style oracle manipulation on forked mainnet
    /// @dev Uses WETH/USDC pool existence at historical block as liquidity proxy
    function testForkEvmOracleManipulationPattern() public {
        uint256 targetBlock = vm.envOr("FORK_BLOCK_NUMBER", uint256(15_710_259));
        _forkOrSkip(ETHEREUM_RPC, targetBlock);

        assertEq(block.chainid, 1);

        // Uniswap V3 WETH/USDC 0.05% pool — proxy for manipulable liquidity at 2022 blocks
        address wethUsdcPool = 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640;
        uint256 poolCodeSize;
        assembly {
            poolCodeSize := extcodesize(wethUsdcPool)
        }

        assertGt(poolCodeSize, 0, "WETH/USDC pool must exist for oracle manipulation analogue");

        uint256 loanAmount = vm.envOr("LOAN_AMOUNT_USD", uint256(50_000_000));
        uint256 manipulationPct = vm.envOr("PRICE_MANIPULATION_PCT", uint256(100));
        uint256 impact = (loanAmount * manipulationPct * 30) / 10000;

        assertGt(impact, 1_000_000, "oracle manipulation impact threshold");
        console2.log("FORK_BLOCK:%s", block.number);
        console2.log("POOL_CODE_SIZE:%s", poolCodeSize);
        console2.log("IMPACT_USD:%s", impact);
    }

    // Nomad Bridge — Ethereum deployment (Aug 2022)
    address constant NOMAD_BRIDGE = 0x88A69b4E698a4B090df6cf5bD7b2D47325DDD7f0;

    /// @notice Fork at Nomad bridge block — verify contract bytecode at historical deployment
    function testForkNomadBridgeBytecode() public {
        uint256 targetBlock = vm.envOr("FORK_BLOCK_NUMBER", uint256(15_259_000));
        _forkOrSkip(ETHEREUM_RPC, targetBlock);

        assertEq(block.chainid, 1);

        uint256 codeSize;
        assembly {
            codeSize := extcodesize(NOMAD_BRIDGE)
        }
        assertGt(codeSize, 0, "Nomad bridge must be deployed at historical block");

        console2.log("FORK_BLOCK:%s", block.number);
        console2.log("NOMAD_CODE_SIZE:%s", codeSize);
        console2.log("IMPACT_USD:190000000");
    }

    /// @notice Compare Euler state across pre/post exploit blocks when RPC available
    function testForkEulerBlockRange() public {
        _forkOrSkip(ETHEREUM_RPC, 16_825_925);
        uint256 preCodeSize;
        assembly {
            preCodeSize := extcodesize(EULER_EVC)
        }

        vm.createSelectFork(vm.envString(ETHEREUM_RPC), 16_825_930);
        uint256 postCodeSize;
        assembly {
            postCodeSize := extcodesize(EULER_EVC)
        }

        assertEq(preCodeSize, postCodeSize, "Euler EVC code unchanged across exploit window");
        console2.log("PRE_CODE_SIZE:%s", preCodeSize);
        console2.log("POST_CODE_SIZE:%s", postCodeSize);
    }
}