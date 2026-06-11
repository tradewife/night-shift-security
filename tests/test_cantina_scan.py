"""Tests for Cantina registry and unified bounty scan."""

from night_shift_security.bounty.discovery_scan import list_programs_for_platform
from night_shift_security.data.cantina_registry import CANTINA_PROGRAMS, list_programs


def test_cantina_registry_has_euler():
    programs = list_programs()
    euler = next(p for p in programs if p.slug == "euler")
    assert euler.platform == "cantina"
    assert euler.max_bounty_usd == 7_500_000
    assert euler.catalog_analogue == "euler-finance-2023"
    assert "cantina.xyz/bounties/" in euler.url


def test_list_programs_all_includes_both_platforms():
    programs = list_programs_for_platform("all", min_max_bounty_usd=1_000_000)
    platforms = {p.platform for p in programs}
    assert "immunefi" in platforms
    assert "cantina" in platforms


def test_cantina_programs_have_templates():
    for program in CANTINA_PROGRAMS:
        assert program.templates
        assert program.catalog_analogue