"""Solana tooling availability detection."""

import os
from pathlib import Path
import shutil
import urllib.error
import urllib.request


def get_solana_rpc() -> str:
    return (
        os.environ.get("SOLANA_MAINNET_RPC_URL", "")
        or os.environ.get("SOLANA_RPC_URL", "")
    ).strip()


def solana_rpc_available(rpc_url: str | None = None) -> bool:
    rpc = (rpc_url or get_solana_rpc()).strip()
    if not rpc:
        return False

    payload = b'{"jsonrpc":"2.0","id":1,"method":"getHealth"}'
    req = urllib.request.Request(
        rpc,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode()
            return "result" in body or "ok" in body.lower()
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def find_solana_test_validator() -> str:
    """Return a usable solana-test-validator path.

    Hermes cron runs with a stripped, non-login PATH, while the Solana installer
    normally places binaries under ~/.local/share/solana/install/active_release/bin.
    """
    candidates = [
        os.environ.get("SOLANA_VALIDATOR_BIN", "").strip(),
        shutil.which("solana-test-validator") or "",
        str(Path.home() / ".local/share/solana/install/active_release/bin/solana-test-validator"),
        str(Path.home() / ".cargo/bin/solana-test-validator"),
        "/usr/local/bin/solana-test-validator",
        "/usr/bin/solana-test-validator",
    ]
    for candidate in candidates:
        if candidate and os.access(candidate, os.X_OK):
            return candidate
    return ""


def solana_validator_available() -> bool:
    return bool(find_solana_test_validator())


def solana_validator_ready() -> bool:
    """Validator replay needs binary + mainnet RPC for account clones."""
    return solana_validator_available() and bool(get_solana_rpc())


def solana_status() -> dict:
    rpc = get_solana_rpc()
    return {
        "configured": bool(rpc),
        "available": solana_rpc_available(rpc) if rpc else False,
        "validator_installed": solana_validator_available(),
        "validator_bin": find_solana_test_validator(),
        "validator_ready": solana_validator_ready(),
        "env_vars": ["SOLANA_MAINNET_RPC_URL", "SOLANA_RPC_URL", "SOLANA_USE_VALIDATOR"],
    }
