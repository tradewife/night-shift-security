"""Solana validator replay targets for historical exploit validation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SolanaTarget:
    """A historical Solana exploit replay target at a specific slot."""

    target_id: str
    exploit_id: str
    name: str
    slot: int
    fixture_test: str
    template_id: str
    program_id: str
    rpc_env_var: str
    description: str


def get_solana_targets() -> list[SolanaTarget]:
    """
    Registry of Solana replay targets.

    Slice 1: Mango (fixture + optional validator clone), Solend, Cashio, Crema.
    """
    return [
        SolanaTarget(
            target_id="mango-markets-2022",
            exploit_id="mango-markets-2022",
            name="Mango Markets Oracle Manipulation",
            slot=152_000_000,
            fixture_test="mango_replay",
            template_id="flash_loan_oracle",
            program_id="4MangoMjqJ2firMokCjjGgoK8d4ATcrPZ96ZFFn7VGk4",
            rpc_env_var="SOLANA_MAINNET_RPC_URL",
            description=(
                "Mango oracle manipulation at slot ~152000000 (Oct 2022). "
                "Slice 1 uses fixture replay; grant-demo mode uses solana-test-validator --clone."
            ),
        ),
        SolanaTarget(
            target_id="solend-whale-2022",
            exploit_id="solend-whale-2022",
            name="Solend Whale Governance Crisis",
            slot=148_000_000,
            fixture_test="solend_replay",
            template_id="governance_capture",
            program_id="So1endDq2YkqhipRh3WViP8FKh4z4iJ8tqjWjJ3CpN",
            rpc_env_var="SOLANA_MAINNET_RPC_URL",
            description="Realms governance hostile takeover via concentrated SLND voting power.",
        ),
        SolanaTarget(
            target_id="cashio-2022",
            exploit_id="cashio-2022",
            name="Cashio Infinite Mint Exploit",
            slot=133_000_000,
            fixture_test="cashio_replay",
            template_id="access_control_escalation",
            program_id="CASHioDuQGno3n3WnSm5n3WnNT3n3WnSm5n3WnNT",
            rpc_env_var="SOLANA_MAINNET_RPC_URL",
            description="Unchecked collateral account allowed infinite stablecoin mint.",
        ),
        SolanaTarget(
            target_id="crema-finance-2022",
            exploit_id="crema-finance-2022",
            name="Crema Finance Flash Loan LP Drain",
            slot=140_000_000,
            fixture_test="crema_replay",
            template_id="composability_risk",
            program_id="6MLxLqiXaaSUpkgZn9tYjKMbPDXvYAU7YFopBGtR3m3",
            rpc_env_var="SOLANA_MAINNET_RPC_URL",
            description="Flash loan manipulated CLMM liquidity before cross-program drain.",
        ),
    ]


def solana_catalog_targets() -> list[SolanaTarget]:
    """Targets with catalog fixtures in slice 1."""
    return list(get_solana_targets())