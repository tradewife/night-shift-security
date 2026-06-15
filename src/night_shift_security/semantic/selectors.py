"""Entrypoint selector and discriminator helpers."""

from __future__ import annotations

import hashlib


def evm_selector(signature: str) -> dict[str, str]:
    """Return a 4-byte EVM selector.

    Prefer Keccak when pycryptodome is available. Fall back to SHA3-256 with an
    explicit algorithm marker so downstream gates do not mistake it for Keccak.
    """
    try:
        from Crypto.Hash import keccak  # type: ignore[import-not-found]

        h = keccak.new(digest_bits=256)
        h.update(signature.encode())
        return {"value": "0x" + h.hexdigest()[:8], "algorithm": "keccak256"}
    except Exception:
        digest = hashlib.sha3_256(signature.encode()).hexdigest()[:8]
        return {"value": "0x" + digest, "algorithm": "sha3_256_fallback"}


def anchor_discriminator(name: str) -> str:
    digest = hashlib.sha256(f"global:{name}".encode()).digest()[:8]
    return "0x" + digest.hex()
