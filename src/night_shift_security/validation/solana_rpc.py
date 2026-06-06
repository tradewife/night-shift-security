"""Solana tooling availability detection."""

import os
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


def solana_validator_available() -> bool:
    return shutil.which("solana-test-validator") is not None


def solana_status() -> dict:
    rpc = get_solana_rpc()
    return {
        "configured": bool(rpc),
        "available": solana_rpc_available(rpc) if rpc else False,
        "validator_installed": solana_validator_available(),
        "env_vars": ["SOLANA_MAINNET_RPC_URL", "SOLANA_RPC_URL", "SOLANA_USE_VALIDATOR"],
    }