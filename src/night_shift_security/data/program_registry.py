"""Unified lookup for Immunefi + Cantina curated programs."""

from __future__ import annotations

from night_shift_security.data.bounty_program import BountyProgram
from night_shift_security.data.cantina_registry import CANTINA_PROGRAMS
from night_shift_security.data.immunefi_registry import IMMUNEFI_PROGRAMS, immunefi_to_bounty


def get_program_by_slug(slug: str, *, platform: str | None = None) -> BountyProgram | None:
    """Resolve a bounty program by slug across Immunefi and Cantina."""
    slug = slug.strip().lower()
    if platform in (None, "", "immunefi"):
        for program in IMMUNEFI_PROGRAMS:
            if program.slug == slug:
                return immunefi_to_bounty(program)
    if platform in (None, "", "cantina"):
        for program in CANTINA_PROGRAMS:
            if program.slug == slug:
                return program
    if platform is not None:
        return None
    for program in CANTINA_PROGRAMS:
        if program.slug == slug:
            return program
    return None


def all_curated_programs() -> list[BountyProgram]:
    return [immunefi_to_bounty(p) for p in IMMUNEFI_PROGRAMS] + list(CANTINA_PROGRAMS)