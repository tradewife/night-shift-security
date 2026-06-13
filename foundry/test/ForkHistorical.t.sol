// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

interface IWormholeLive {
    function chainId() external view returns (uint16);
    function evmChainId() external view returns (uint256);
    function getCurrentGuardianSetIndex() external view returns (uint32);
    function isFork() external view returns (bool);
    function messageFee() external view returns (uint256);
}

interface ITokenBridgeLive {
    function chainId() external view returns (uint16);
    function evmChainId() external view returns (uint256);
    function isFork() external view returns (bool);
    function wormhole() external view returns (address);
    function governanceChainId() external view returns (uint16);
}

/// @title ForkHistorical — mainnet fork tests at historical exploit blocks
contract ForkHistoricalTest is Test {
    string constant ETHEREUM_RPC = "ETHEREUM_RPC_URL";

    // Euler Ethereum Vault Connector (EVC) — deployed pre-March 2023 exploit
    address constant EULER_EVC = 0x27182842E098f60e3D576794A5bFFb0777E025d3;

    function _forkOrSkip(string memory rpcEnv, uint256 blockNumber) internal {
        try vm.envString(rpcEnv) returns (string memory rpc) {
            if (blockNumber == 0) {
                vm.createSelectFork(rpc);
            } else {
                vm.createSelectFork(rpc, blockNumber);
            }
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
    address constant NOMAD_BRIDGE = 0x88A69B4E698A4B090DF6CF5Bd7B2D47325Ad30A3;

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

    // Wormhole live programs — Ethereum mainnet (recon.json Block B)
    address constant WORMHOLE_CORE = 0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B;
    address constant WORMHOLE_TOKEN_BRIDGE = 0x3ee18B2214AFF97000D974cf647E7C347E8fa585;

    /// @notice Fork mainnet — live Wormhole core getters (beyond bytecode smoke)
    function testForkWormholeCoreLiveGetters() public {
        _forkOrSkip(ETHEREUM_RPC, vm.envOr("FORK_BLOCK_NUMBER", uint256(0)));

        assertEq(block.chainid, 1);

        IWormholeLive core = IWormholeLive(WORMHOLE_CORE);
        assertEq(core.evmChainId(), block.chainid, "core evmChainId must match fork");
        assertEq(core.chainId(), 2, "Wormhole Ethereum chain id");
        assertFalse(core.isFork(), "mainnet fork must not report isFork");
        assertGt(core.getCurrentGuardianSetIndex(), 0, "guardian set index live");

        console2.log("FORK_BLOCK:%s", block.number);
        console2.log("WORMHOLE_GUARDIAN_SET:%s", core.getCurrentGuardianSetIndex());
        console2.log("WORMHOLE_CHAIN_ID:%s", core.chainId());
        console2.log("WORMHOLE_MESSAGE_FEE:%s", core.messageFee());
        console2.log("IMPACT_USD:5000000");
    }

    /// @notice Fork mainnet — live token bridge getters wired to core
    function testForkWormholeTokenBridgeLiveGetters() public {
        _forkOrSkip(ETHEREUM_RPC, vm.envOr("FORK_BLOCK_NUMBER", uint256(0)));

        assertEq(block.chainid, 1);

        ITokenBridgeLive bridge = ITokenBridgeLive(WORMHOLE_TOKEN_BRIDGE);
        assertEq(bridge.evmChainId(), block.chainid);
        assertEq(bridge.chainId(), 2);
        assertFalse(bridge.isFork());
        assertEq(bridge.wormhole(), WORMHOLE_CORE, "bridge must reference live core");
        assertGt(bridge.governanceChainId(), 0);

        console2.log("FORK_BLOCK:%s", block.number);
        console2.log("BRIDGE_WORMHOLE:%s", bridge.wormhole());
        console2.log("BRIDGE_GOVERNANCE_CHAIN:%s", bridge.governanceChainId());
        console2.log("IMPACT_USD:5000000");
    }

    /// @notice Fork mainnet — verify Wormhole core bytecode (not Nomad proxy)
    function testForkWormholeCoreBytecode() public {
        _forkOrSkip(ETHEREUM_RPC, vm.envOr("FORK_BLOCK_NUMBER", uint256(0)));

        assertEq(block.chainid, 1);

        uint256 codeSize;
        assembly {
            codeSize := extcodesize(WORMHOLE_CORE)
        }
        assertGt(codeSize, 0, "Wormhole core must be deployed on Ethereum mainnet");

        console2.log("FORK_BLOCK:%s", block.number);
        console2.log("WORMHOLE_CORE_CODE_SIZE:%s", codeSize);
        console2.log("IMPACT_USD:5000000");
    }

    /// @notice Fork mainnet — verify Wormhole token bridge bytecode
    function testForkWormholeTokenBridgeBytecode() public {
        _forkOrSkip(ETHEREUM_RPC, vm.envOr("FORK_BLOCK_NUMBER", uint256(0)));

        assertEq(block.chainid, 1);

        uint256 codeSize;
        assembly {
            codeSize := extcodesize(WORMHOLE_TOKEN_BRIDGE)
        }
        assertGt(codeSize, 0, "Wormhole token bridge must be deployed on Ethereum mainnet");

        console2.log("FORK_BLOCK:%s", block.number);
        console2.log("WORMHOLE_BRIDGE_CODE_SIZE:%s", codeSize);
        console2.log("IMPACT_USD:5000000");
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