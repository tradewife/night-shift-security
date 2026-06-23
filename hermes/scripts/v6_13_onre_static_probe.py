"""OnRe v6.13 static probe for Token-2022 redemption accounting asymmetry."""

from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ONRE = ROOT / "sources" / "onre" / "repo"
OUT = ROOT / "data" / "security_results" / "investigations" / "2026-06-22-v6-13-onre-deep-dive"


def _contains(path: Path, needle: str) -> bool:
    return needle in path.read_text()


def main() -> int:
    token_utils = ONRE / "programs" / "onreapp" / "src" / "utils" / "token_utils.rs"
    redemption_utils = ONRE / "programs" / "onreapp" / "src" / "instructions" / "redemption" / "redemption_utils.rs"
    create_request = ONRE / "programs" / "onreapp" / "src" / "instructions" / "redemption" / "create_redemption_request.rs"
    cancel_request = ONRE / "programs" / "onreapp" / "src" / "instructions" / "redemption" / "cancel_redemption_request.rs"

    offer_guard = (
        _contains(token_utils, "pub fn execute_token_operations")
        and _contains(token_utils, "has_transfer_fee(params.token_in_mint)?")
        and _contains(token_utils, "has_transfer_fee(params.token_out_mint)?")
    )
    redemption_missing_guard = (
        _contains(redemption_utils, "pub fn execute_redemption_operations")
        and "has_transfer_fee" not in redemption_utils.read_text()
    )
    records_gross_amount = _contains(create_request, "redemption_request.amount = amount;")
    transfers_gross_amount_on_cancel = (
        _contains(cancel_request, "let amount = redemption_request.amount;")
        and _contains(cancel_request, "amount,")
    )

    candidate = {
        "candidate_schema_version": 4,
        "target_pinned": True,
        "source_ref": {
            "repo": "https://github.com/onre-finance/onre-sol",
            "commit": "361cd588ba48b89a44236801140cdc2b5d110251",
            "program": "onreuGhHHgVzMWSkj2oQDLDtvvGvoepBPkqyaubFcwe",
        },
        "entrypoint": {
            "instruction": "create_redemption_request",
            "followups": ["cancel_redemption_request", "fulfill_redemption_request"],
        },
        "reproduction_artifact": "data/security_results/investigations/2026-06-22-v6-13-onre-deep-dive/evidence/token2022_transfer_fee_poc.spec.ts",
        "impact_oracle": {
            "measured": False,
            "reason": "static_probe_only_build_blocked",
        },
        "failure_trace": {
            "blocking": True,
            "reason": "OnRe SBF build blocked on host toolchain and Docker pull timeout",
        },
    }

    envelope = {
        "schema_version": "v6.13-onre-static-probe.v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "target": "onre",
        "classification": (
            "executable_scaffold_unconfirmed_candidate"
            if all(
                [
                    offer_guard,
                    redemption_missing_guard,
                    records_gross_amount,
                    transfers_gross_amount_on_cancel,
                ]
            )
            else "no_static_signal"
        ),
        "checks": {
            "offer_path_blocks_transfer_fee": offer_guard,
            "redemption_path_missing_transfer_fee_guard": redemption_missing_guard,
            "create_request_records_gross_amount": records_gross_amount,
            "cancel_uses_recorded_gross_amount": transfers_gross_amount_on_cancel,
        },
        "candidate": candidate,
        "submit_ready": False,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "onre_static_probe.json").write_text(json.dumps(envelope, indent=2) + "\n")
    print(json.dumps(envelope, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
