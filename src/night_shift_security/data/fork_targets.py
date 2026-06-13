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