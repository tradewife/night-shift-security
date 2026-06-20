"""Update submittable/manifest.json + native_harness_status.json for v6.1 calibration outcome."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    # manifest.json update: keep pack_count=0 (no submit-ready finding); only record outcome.
    manifest_path = Path("data/security_results/bounty/submittable/manifest.json")
    manifest_data = {
        "schema_version": "2.0",
        "source": "night-shift-security",
        "export_track": "submittable",
        "generated_at": _utc_now(),
        "run_at": _utc_now(),
        "pack_count": 0,
        "grading_track": "shoestring",
        "calibration_lane": True,
        "packs": [],
        "v6_1_observations": {
            "spec_version": "v6.1.0-proposal-session5",
            "calibration_target": "ethena_native (EthenaMinting V1)",
            "calibration_lane_pack": "data/security_results/bounty/submittable/ethena/NSS-CALIB-1.json",
            "calibration_gate_trace": "data/security_results/bounty/submittable/ethena/nss-calib-1-gate-trace.json",
            "calibration_outcome": {
                "submit_ready_achieved": False,
                "first_quantitative_false_negative_datum": True,
                "bug_class_present_in_production": True,
                "bug_class_exploitable_for_direct_extraction": False,
                "gate_blame_for_honest_zero": "_v4_candidate_submission_ok (impact_oracle.measured=False)",
                "spec_action": "no gate loosening applied; calibration outcome recorded honestly per SPEC v6.1 §5",
            },
        },
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2))

    # native_harness_status.json update: leave ethena_native as scaffolded (per probe outcome)
    status_path = Path("data/security_results/loop/native_harness_status.json")
    status = json.loads(status_path.read_text())
    if "ethena_native" in status.get("harnesses", {}):
        status["harnesses"]["ethena_native"]["status"] = "scaffolded"
        status["harnesses"]["ethena_native"]["last_updated"] = _utc_now()
        status["harnesses"]["ethena_native"]["notes"] = (
            "v6.1 §5 empirical calibration probe (foundry/test/EthenaCalibrationProbe.t.sol) "
            "CONFIRMED the uint64/nonce-collision bug class in production bytecode (Lane A) and "
            "CONFIRMED it is NOT exploitable for direct USDe extraction (Lane B). Honest-zero "
            "outcome. NativeHarness stays at status=scaffolded because impact_oracle.measured=False. "
            "Required before promotion to 'ready': a different probe class (e.g., denial-of-mint "
            "with delegated signer access in WHITELIST mode) yields a measurable delta."
        )

    status["generated_at"] = _utc_now()
    status["action"] = "calibration_lane_honest_zero"
    status_path.write_text(json.dumps(status, indent=2))
    print("manifest ->", manifest_path)
    print("native_harness_status.ethena_native updated to status=scaffolded (calibration_honest_zero)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
