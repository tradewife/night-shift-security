"""Mainnet fork targets for historical exploit validation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ForkTarget:
    """A historical exploit replay target on a specific chain/block."""

    target_id: str
    exploit_id: str
    name: str
    chain: str
    chain_id: int
    block_number: int
    fork_test: str
    template_id: str
    contract_address: str
    rpc_env_var: str
    description: str
    solana: bool = False


def get_fork_targets() -> list[ForkTarget]:
    """
    Registry of fork replay targets.

    Euler: Ethereum mainnet (EVM) — Foundry fork test.
    Mango: Solana — catalog/mock validation only (no EVM fork).
    """
    return [
        ForkTarget(
            target_id="euler-finance-2023",
            exploit_id="euler-finance-2023",
            name="Euler Finance Donate-to-Reentrancy",
            chain="ethereum",
            chain_id=1,
            block_number=16_825_925,
            fork_test="testForkEulerHistoricalBlock",
            template_id="reentrancy",
            contract_address="0x27182842e098f60e3d576794a5bffb0777e025d3",
            rpc_env_var="ETHEREUM_RPC_URL",
            description=(
                "Euler EVC at block 16825925 (March 13 2023, ~pre-exploit state). "
                "Validates contract deployment and chain state at historical block."
            ),
        ),
        ForkTarget(
            target_id="euler-finance-2023-post",
            exploit_id="euler-finance-2023",
            name="Euler Finance Post-Exploit Block",
            chain="ethereum",
            chain_id=1,
            block_number=16_825_930,
            fork_test="testForkEulerHistoricalBlock",
            template_id="reentrancy",
            contract_address="0x27182842e098f60e3d576794a5bffb0777e025d3",
            rpc_env_var="ETHEREUM_RPC_URL",
            description="Block immediately after Euler exploit for state comparison.",
        ),
        ForkTarget(
            target_id="nomad-bridge-2022",
            exploit_id="nomad-bridge-2022",
            name="Nomad Bridge EVM Replica",
            chain="ethereum",
            chain_id=1,
            block_number=15_259_000,
            fork_test="testForkNomadBridgeBytecode",
            template_id="access_control_escalation",
            contract_address="0x88a69b4e698a4b090df6cf5bd7b2d47325ad30a3",
            rpc_env_var="ETHEREUM_RPC_URL",
            description=(
                "Nomad bridge contract at block 15259000 (Aug 2022, pre-mass-drain). "
                "Validates bytecode deployment for access-control escalation replay."
            ),
        ),
        ForkTarget(
            target_id="wormhole-core-ethereum",
            exploit_id="wormhole-live-core",
            name="Wormhole Core (Ethereum)",
            chain="ethereum",
            chain_id=1,
            block_number=0,
            fork_test="testForkWormholeCoreGovernanceSurface",
            template_id="access_control_escalation",
            contract_address="0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B",
            rpc_env_var="ETHEREUM_RPC_URL",
            description=(
                "Live Wormhole core contract on Ethereum mainnet "
                "(sources/wormhole/recon.json). Governance/quorum surface — triage-scoped."
            ),
        ),
        ForkTarget(
            target_id="wormhole-token-bridge-value-probe-ethereum",
            exploit_id="wormhole-live-token-bridge-value-probe",
            name="Wormhole Token Bridge Value Probe (Ethereum)",
            chain="ethereum",
            chain_id=1,
            block_number=0,
            fork_test="testForkWormholeInvalidCompleteTransferNoUsdcDelta",
            template_id="composability_risk",
            contract_address="0x3ee18B2214AFF97000D974cf647E7C347E8fa585",
            rpc_env_var="ETHEREUM_RPC_URL",
            description=(
                "Live Wormhole token bridge value-movement negative probe on Ethereum mainnet. "
                "Malformed completion must not change USDC bridge balance or outstanding accounting."
            ),
        ),
        ForkTarget(
            target_id="wormhole-token-bridge-ethereum",
            exploit_id="wormhole-live-token-bridge",
            name="Wormhole Token Bridge (Ethereum)",
            chain="ethereum",
            chain_id=1,
            block_number=0,
            fork_test="testForkWormholeBridgeGovernanceSurface",
            template_id="composability_risk",
            contract_address="0x3ee18B2214AFF97000D974cf647E7C347E8fa585",
            rpc_env_var="ETHEREUM_RPC_URL",
            description=(
                "Live Wormhole token bridge on Ethereum mainnet "
                "(sources/wormhole/recon.json). Bridge governance/transfer ledger surface."
            ),
        ),
        ForkTarget(
            target_id="wormhole-token-bridge-pauser-ethereum",
            exploit_id="wormhole-live-token-bridge-pauser",
            name="Wormhole Token Bridge Pauser Auth (Ethereum)",
            chain="ethereum",
            chain_id=1,
            block_number=0,
            fork_test="testForkWormholeBridgePauserAuthSurface",
            template_id="access_control_escalation",
            contract_address="0x3ee18B2214AFF97000D974cf647E7C347E8fa585",
            rpc_env_var="ETHEREUM_RPC_URL",
            description=(
                "Live Wormhole token bridge pause/unpause auth on Ethereum mainnet. "
                "Non-pauser/unpauser callers must revert NotPauser/NotUnpauser."
            ),
        ),
        ForkTarget(
            target_id="beanstalk-governance-2022",
            exploit_id="beanstalk-2022",
            name="Beanstalk Governance Flash-Loan Pattern",
            chain="ethereum",
            chain_id=1,
            block_number=14_421_000,
            fork_test="testForkEvmOracleManipulationPattern",
            template_id="governance_capture",
            contract_address="0xC1E088fC1323b20BCBee4bdC4104fC1a960E67C8",
            rpc_env_var="ETHEREUM_RPC_URL",
            description=(
                "Beanstalk governance flash-loan analogue for Reserve Protocol Cantina hunts. "
                "Uses EVM oracle/governance pattern test at historical block."
            ),
        ),
        ForkTarget(
            target_id="polymarket-polygon-nomad-analogue",
            exploit_id="nomad-bridge-2022",
            name="Polymarket Polygon Access-Control Analogue",
            chain="polygon",
            chain_id=137,
            block_number=30_000_000,
            fork_test="testForkNomadBridgeBytecode",
            template_id="access_control_escalation",
            contract_address="0x88a69B4E698A4B090DF6CF5Bd7B2D47325Ad30A3",
            rpc_env_var="POLYGON_RPC_URL",
            description=(
                "Polymarket Cantina — Polygon fork harness via Nomad bridge bytecode probe. "
                "Falls back to Ethereum nomad test when POLYGON_RPC_URL unavailable."
            ),
        ),
        ForkTarget(
            target_id="mango-markets-2022",
            exploit_id="mango-markets-2022",
            name="Mango Markets Oracle Manipulation",
            chain="solana",
            chain_id=0,
            block_number=0,
            fork_test="",
            template_id="flash_loan_oracle",
            contract_address="",
            rpc_env_var="SOLANA_RPC_URL",
            description=(
                "Mango exploit occurred on Solana (slot ~152000000, Oct 2022). "
                "EVM Foundry cannot fork Solana — validated via Python catalog + "
                "EVM analogue test testForkEvmOracleManipulationPattern."
            ),
            solana=True,
        ),
    ]


def evm_fork_targets() -> list[ForkTarget]:
    return [t for t in get_fork_targets() if not t.solana]
