"""Per-target hypothesis sequence emitters (v5 Phase 10, defect D6)."""

from night_shift_security.hypothesis.concrete_sequences import (
    CallSequence,
    InstructionSequence,
    emit_concrete_sequences,
    native_status_for_slug,
    sequences_for_slug,
)

__all__ = [
    "CallSequence",
    "InstructionSequence",
    "emit_concrete_sequences",
    "native_status_for_slug",
    "sequences_for_slug",
]