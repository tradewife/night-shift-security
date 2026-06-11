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
    validator_backed: bool = False
    clone_accounts: tuple[str, ...] = ()


def get_solana_targets() -> list[SolanaTarget]:
    """
    Registry of Solana replay targets.

    Slice 2–3: Solend, Cashio, Mango validator-backed; Crema fixture-only.
    """
    return [
        SolanaTarget(
            target_id="mango-markets-2022",
            exploit_id="mango-markets-2022",
            name="Mango Markets Oracle Manipulation",
            slot=152_000_000,
            fixture_test="mango_replay",
            template_id="flash_loan_oracle",
            program_id="4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg",
            rpc_env_var="SOLANA_MAINNET_RPC_URL",
            description=(
                "Mango oracle manipulation at slot ~152000000 (Oct 2022). "
                "Validator-backed in Slice 3."
            ),
            validator_backed=True,
            clone_accounts=("4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg",),
        ),
        SolanaTarget(
            target_id="solend-whale-2022",
            exploit_id="solend-whale-2022",
            name="Solend Whale Governance Crisis",
            slot=139_896_000,
            fixture_test="solend_replay",
            template_id="governance_capture",
            program_id="So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo",
            rpc_env_var="SOLANA_MAINNET_RPC_URL",
            description=(
                "Realms governance hostile takeover via concentrated SLND voting power "
                "(Jun 2022, slot ~139896000). Validator-backed in Slice 2."
            ),
            validator_backed=True,
            clone_accounts=("So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo",),
        ),
        SolanaTarget(
            target_id="cashio-2022",
            exploit_id="cashio-2022",
            name="Cashio Infinite Mint Exploit",
            slot=128_587_000,
            fixture_test="cashio_replay",
            template_id="access_control_escalation",
            program_id="BRRRot6ig147TBU6EGp7TMesmQrwu729CbG6qu2ZUHWm",
            rpc_env_var="SOLANA_MAINNET_RPC_URL",
            description=(
                "Unchecked collateral account allowed infinite stablecoin mint "
                "(Mar 2022, slot ~128587000). Validator-backed in Slice 2."
            ),
            validator_backed=True,
            clone_accounts=(
                "BRRRot6ig147TBU6EGp7TMesmQrwu729CbG6qu2ZUHWm",
                "BANKhiCgEYd7QmcWwPLkqvTuuLN6qEwXDZgTe6HEbwv1",
            ),
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
            description="Flash loan manipulated CLMM liquidity before cross-program drain. Fixture-only.",
            validator_backed=False,
        ),
    ]


def solana_catalog_targets() -> list[SolanaTarget]:
    """All catalog Solana anchor targets."""
    return list(get_solana_targets())


def validator_backed_targets() -> list[SolanaTarget]:
    """Exploits with real solana-test-validator clone replay in Slice 2."""
    return [t for t in get_solana_targets() if t.validator_backed]