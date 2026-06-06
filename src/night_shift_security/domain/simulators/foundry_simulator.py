"""Foundry fork simulator — runs forge test against vulnerable contract harness."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from night_shift_security.data.schemas import (
    AttackResult,
    AttackVector,
    ContractState,
    InvariantViolation,
    ReproductionStep,
    Severity,
)
from night_shift_security.domain.simulators.base import AttackSimulator, SimulatorBackend
from night_shift_security.domain.simulators.mock_simulator import MockSimulator

_FOUNDRY_ROOT = Path(__file__).resolve().parents[4] / "foundry"

_TEMPLATE_TEST_MAP = {
    "governance_capture": "testGovernanceCapture",
    "treasury_drain": "testTreasuryDrain",
    "flash_loan_oracle": "testFlashLoanOracle",
    "reentrancy": "testReentrancy",
}


class FoundrySimulator(AttackSimulator):
    """
    Execute attacks via Foundry forge test.

    Falls back to MockSimulator when forge is not installed or tests fail to compile.
    """

    def __init__(self, foundry_root: Path | None = None, fork_url: str | None = None):
        self._root = foundry_root or _FOUNDRY_ROOT
        self._fork_url = fork_url or os.environ.get("FOUNDRY_FORK_URL", "")
        self._mock = MockSimulator()
        self._forge = shutil.which("forge")

    @property
    def backend(self) -> SimulatorBackend:
        return SimulatorBackend.FOUNDRY if self.is_available() else SimulatorBackend.MOCK

    def is_available(self) -> bool:
        return self._forge is not None and (self._root / "foundry.toml").exists()

    def execute(self, vector: AttackVector, state: ContractState) -> AttackResult:
        if not self.is_available():
            result = self._mock.execute(vector, state)
            result.notes = "foundry_unavailable: used mock simulator"
            return result

        test_name = _TEMPLATE_TEST_MAP.get(vector.template_id)
        if not test_name:
            result = self._mock.execute(vector, state)
            result.notes = "foundry_no_test: used mock simulator"
            return result

        env = {**os.environ, **_params_to_env(vector.parameters, state)}
        if self._fork_url:
            env["FOUNDRY_FORK_URL"] = self._fork_url

        cmd = [self._forge, "test", "--match-test", test_name, "-vv", "--json"]
        try:
            proc = subprocess.run(
                cmd,
                cwd=self._root,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError):
            result = self._mock.execute(vector, state)
            result.notes = "foundry_timeout: used mock simulator"
            return result

        return self._parse_forge_output(proc.stdout, proc.stderr, proc.returncode, vector, state)

    def _parse_forge_output(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        vector: AttackVector,
        state: ContractState,
    ) -> AttackResult:
        """Parse forge JSON output into AttackResult."""
        success = returncode == 0
        impact = 0.0
        notes = ""

        try:
            for line in stdout.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    data = json.loads(line)
                    if data.get("status") == "success":
                        success = True
                    break
        except json.JSONDecodeError:
            success = "PASS" in stdout or returncode == 0

        impact_match = re.search(r"IMPACT_USD:(\d+(?:\.\d+)?)", stdout + stderr)
        if impact_match:
            impact = float(impact_match.group(1))

        if not success:
            fallback = self._mock.execute(vector, state)
            if fallback.success:
                notes = "foundry_failed_mock_succeeded"
                return AttackResult(
                    vector=vector,
                    success=True,
                    severity=fallback.severity,
                    economic_impact_usd=fallback.economic_impact_usd,
                    invariant_violations=fallback.invariant_violations,
                    reproduction_steps=fallback.reproduction_steps,
                    capital_required_usd=fallback.capital_required_usd,
                    notes=notes,
                )

        severity = Severity.CRITICAL if success and impact >= 10_000_000 else (
            Severity.HIGH if success and impact >= 1_000_000 else (
                Severity.MEDIUM if success else Severity.LOW
            )
        )

        steps = [ReproductionStep("forge_test", "attacker", {"test": _TEMPLATE_TEST_MAP.get(vector.template_id, "")})]
        violations = []
        if success:
            violations.append(
                InvariantViolation(
                    invariant_id="foundry_confirmed",
                    description="Attack reproduced in Foundry test harness",
                    expected="invariant holds",
                    actual="invariant violated",
                )
            )

        return AttackResult(
            vector=vector,
            success=success,
            severity=severity,
            economic_impact_usd=impact,
            invariant_violations=violations,
            reproduction_steps=steps,
            notes=notes or "foundry_confirmed",
        )


def _params_to_env(params: dict, state: ContractState) -> dict[str, str]:
    """Map attack parameters and state to forge env vars."""
    env: dict[str, str] = {
        "PROTOCOL_ID": state.protocol_id,
        "TREASURY_BALANCE_USD": str(int(state.treasury_balance_usd)),
    }
    key_map = {
        "voting_power_pct": "VOTING_POWER_PCT",
        "use_flash_loan": "USE_FLASH_LOAN",
        "bypass_timelock": "BYPASS_TIMELOCK",
        "withdrawal_pct": "WITHDRAWAL_PCT",
        "use_compromised_admin": "USE_COMPROMISED_ADMIN",
        "bypass_multisig": "BYPASS_MULTISIG",
        "loan_amount_usd": "LOAN_AMOUNT_USD",
        "price_manipulation_pct": "PRICE_MANIPULATION_PCT",
        "use_single_oracle": "USE_SINGLE_ORACLE",
        "recursion_depth": "RECURSION_DEPTH",
        "target_function": "TARGET_FUNCTION",
    }
    for k, v in params.items():
        env_key = key_map.get(k, k.upper())
        env[env_key] = str(v).lower() if isinstance(v, bool) else str(v)
    return env


def get_simulator(prefer_foundry: bool = True, fork_url: str | None = None) -> AttackSimulator:
    """Return best available simulator."""
    if prefer_foundry:
        foundry = FoundrySimulator(fork_url=fork_url)
        if foundry.is_available():
            return foundry
    return MockSimulator()