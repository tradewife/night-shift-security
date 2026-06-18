#!/usr/bin/env python3
"""Seed concrete_candidates from native harness discriminators (no repo clone)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from night_shift_security.knowledge.concrete_candidates import upsert_candidates
from night_shift_security.native import jito, kamino, orca, raydium
from night_shift_security.semantic.candidates import ConcreteCandidate

MODULES = {
    "kamino": (kamino, kamino.KLEND_PROGRAM, "solana"),
    "jito": (jito, jito.SPL_STAKE_POOL_PROGRAM, "solana"),
    "raydium": (raydium, raydium.CLMM_PROGRAM, "solana"),
    "orca": (orca, orca.WHIRLPOOL_PROGRAM, "solana"),
}


def main() -> int:
    store = REPO / "data" / "security_results" / "knowledge" / "concrete_candidates.jsonl"
    for slug, (mod, program_id, chain) in MODULES.items():
        candidates: list[ConcreteCandidate] = []
        for i, (name, disc) in enumerate(mod.discriminators().items()):
            candidates.append(
                ConcreteCandidate(
                    candidate_id=f"{slug}-native-{i:03d}",
                    target_slug=slug,
                    campaign_id=f"v5-native-{slug}",
                    chain=chain,
                    source_ref={"commit": "native-harness-v5", "module": mod.__name__},
                    entrypoint={
                        "name": name,
                        "discriminator": disc,
                        "program_id": program_id,
                    },
                    actors=[],
                    state_bindings={"market_hint": getattr(mod, "DEFAULT_MARKET_PUBKEY", "")},
                    sequence=[{"step": name, "discriminator": disc}],
                    invariant={"id": "value_flow_sanity", "predicate": "no_unauthorized_mint"},
                    impact_oracle={"measured": False},
                    provenance={"source": "native_harness_seed"},
                )
            )
        stats = upsert_candidates(candidates, path=store, replace_target_slug=slug, replace_provenance_source="native_harness_seed")
        print(f"{slug}: upserted {stats['upserted']} -> {stats['after']} total rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())