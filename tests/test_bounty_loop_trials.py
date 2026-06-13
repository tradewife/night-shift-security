"""Tests for bounty loop N-trial execution."""

from unittest.mock import patch

from night_shift_security.orchestration.bounty_loop import run_bounty_loop


def _mock_iteration(**kwargs):
    trial = kwargs.get("trial_index", 0)
    pinned = kwargs.get("pinned_target")
    if pinned:
        slug = pinned["slug"]
        platform = pinned["platform"]
    else:
        slug = "kamino"
        platform = "immunefi"
    return {
        "status": "continue",
        "target": {"slug": slug, "platform": platform, "name": "Kamino"},
        "trial_index": trial,
    }


def test_run_bounty_loop_trials_pins_target():
    with patch(
        "night_shift_security.orchestration.bounty_loop.run_loop_iteration",
        side_effect=_mock_iteration,
    ) as mock_iter:
        result = run_bounty_loop(iterations=1, trials=3, refresh_scan=False)

    assert result["trials_per_target"] == 3
    assert result["iterations_run"] == 3
    assert mock_iter.call_count == 3
    pinned_calls = [c for c in mock_iter.call_args_list if c.kwargs.get("pinned_target")]
    assert len(pinned_calls) == 2
    assert pinned_calls[0].kwargs["pinned_target"] == {
        "slug": "kamino",
        "platform": "immunefi",
    }