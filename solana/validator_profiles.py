"""Validator clone profiles for Slice 2 validator-backed Solana exploits."""

from dataclasses import dataclass

from klend_account_discovery import klend_clone_data_accounts

FARMS_PROGRAM = "FarmsPZpWu9i7Kky8tPN37rs2TpmMrAZrC7S7vJa91Hr"


@dataclass(frozen=True)
class ValidatorProfile:
    exploit_id: str
    historical_slot: int
    clone_accounts: tuple[str, ...]
    impact_usd: float
    impact_lamports: int
    notes: str
    clone_data_accounts: tuple[str, ...] = ()


# Historical slots are documented reference points (June 2022 Solend whale vote,
# March 2022 Cashio infinite mint). solana-test-validator --clone pulls current
# mainnet account state from RPC; we verify program deployment on the local ledger.
VALIDATOR_PROFILES: dict[str, ValidatorProfile] = {
    "solend-whale-2022": ValidatorProfile(
        exploit_id="solend-whale-2022",
        historical_slot=139_896_000,
        clone_accounts=(
            "So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo",
        ),
        impact_usd=25_000_000,
        impact_lamports=166_666_666_667,
        notes="Solend lending program + Realms governance crisis (~Jun 19 2022, slot ~139.9M).",
    ),
    "cashio-2022": ValidatorProfile(
        exploit_id="cashio-2022",
        historical_slot=128_587_000,
        clone_accounts=(
            "BRRRot6ig147TBU6EGp7TMesmQrwu729CbG6qu2ZUHWm",
            "BANKhiCgEYd7QmcWwPLkqvTuuLN6qEwXDZgTe6HEbwv1",
        ),
        impact_usd=52_000_000,
        impact_lamports=346_666_666_667,
        notes="Cashio brrr + bankman programs (~Mar 23 2022, slot ~128.6M).",
    ),
    "mango-markets-2022": ValidatorProfile(
        exploit_id="mango-markets-2022",
        historical_slot=152_000_000,
        clone_accounts=(
            "4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg",
        ),
        impact_usd=110_000_000,
        impact_lamports=733_333_333_333,
        notes="Mango Markets program (~Oct 2022 oracle manipulation, slot ~152M). Slice 3.",
    ),
    "kamino-klend": ValidatorProfile(
        exploit_id="kamino-klend",
        historical_slot=245_000_000,
        clone_accounts=(
            "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD",
            "KvauGMspG5k6rtzrqqn7WNn3oZdyKqLKwK2XWQ8FLjd",
            "HFn8GnPADiny6XqUoWE8uRPPxb29ikn4yTuPa9MF2fWJ",
            FARMS_PROGRAM,
        ),
        clone_data_accounts=klend_clone_data_accounts(),
        impact_usd=5_000_000,
        impact_lamports=33_333_333_333,
        notes=(
            "Kamino KLend + KVault + oracle + farms programs plus mainnet lending market, "
            "authority, and USDC/SOL reserve vaults (sources/kamino/klend_accounts.json)."
        ),
    ),
}


def validator_backed_exploit_ids() -> frozenset[str]:
    return frozenset(VALIDATOR_PROFILES.keys())


def get_validator_profile(exploit_id: str) -> ValidatorProfile | None:
    return VALIDATOR_PROFILES.get(exploit_id)
