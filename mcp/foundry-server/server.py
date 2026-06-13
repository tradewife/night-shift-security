#!/usr/bin/env python3
"""MCP server exposing Foundry forge/cast/anvil tools to Hermes and Cursor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from mcp.server.fastmcp import FastMCP

from night_shift_security.operator.foundry_tools import (
    run_cast_call,
    run_forge_test,
    start_anvil_fork,
    stop_anvil_fork,
)

mcp = FastMCP("nss-foundry")


@mcp.tool()
def forge_test(
    match_test: str,
    fork_block: int | None = None,
    fork_url: str | None = None,
) -> str:
    """Run forge test --match-test in the NSS foundry harness."""
    result = run_forge_test(
        match_test=match_test,
        fork_block=fork_block,
        fork_url=fork_url,
    )
    return json.dumps(result.to_dict(), indent=2)


@mcp.tool()
def cast_call(
    to: str,
    signature: str,
    args: list[str] | None = None,
    rpc_url: str | None = None,
    from_addr: str | None = None,
) -> str:
    """Execute cast call against fork or sandbox RPC."""
    result = run_cast_call(
        to=to,
        signature=signature,
        args=args,
        rpc_url=rpc_url,
        from_addr=from_addr,
    )
    return json.dumps(result.to_dict(), indent=2)


@mcp.tool()
def anvil_fork(
    fork_block: int | None = None,
    fork_url: str | None = None,
    port: int = 8545,
    attacker: str | None = None,
    use_docker: bool = False,
) -> str:
    """Start Anvil mainnet fork with funded attacker (local or Docker sandbox)."""
    result = start_anvil_fork(
        fork_url=fork_url,
        fork_block=fork_block,
        port=port,
        attacker=attacker,
        use_docker=use_docker,
    )
    return json.dumps(result.to_dict(), indent=2)


@mcp.tool()
def anvil_stop() -> str:
    """Stop local Anvil fork started by anvil_fork."""
    result = stop_anvil_fork()
    return json.dumps(result.to_dict(), indent=2)


if __name__ == "__main__":
    mcp.run()