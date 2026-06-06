"""RPC availability detection for live mainnet fork validation."""

import os
import urllib.error
import urllib.request


def get_ethereum_rpc() -> str:
    """Return configured Ethereum RPC URL, if any."""
    return (
        os.environ.get("ETHEREUM_RPC_URL", "")
        or os.environ.get("FOUNDRY_FORK_URL", "")
        or os.environ.get("ETH_RPC_URL", "")
    ).strip()


def rpc_available(rpc_url: str | None = None) -> bool:
    """Check whether an Ethereum JSON-RPC endpoint responds."""
    rpc = (rpc_url or get_ethereum_rpc()).strip()
    if not rpc:
        return False

    payload = b'{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
    req = urllib.request.Request(
        rpc,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode()
            return "result" in body
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def rpc_status() -> dict:
    """Summary for pipeline logging."""
    rpc = get_ethereum_rpc()
    return {
        "configured": bool(rpc),
        "available": rpc_available(rpc) if rpc else False,
        "env_vars": ["ETHEREUM_RPC_URL", "FOUNDRY_FORK_URL", "ETH_RPC_URL"],
    }