"""Tests for action scoring (being rebuilt).

The scoring module is being reconstructed from scratch around
`evaluate_state` + `score_action`. These tests cover the pieces that exist
so far; per-action cost / reward / future-value tests will be added back as
those functions are reintroduced.
"""
from src.domains.player.player import Player
from src.domains.player.scoring import (
    evaluate_state,
    score_action,
    score_valid_actions,
)


class TestEvaluateState:
    """`evaluate_state` — placeholder state evaluator (body is `...`)."""

    def test_callable_on_player(self):
        """evaluate_state runs without raising on a built player."""
        player = Player().build()
        # Stub body is `...` → returns None. Just assert it runs.
        assert evaluate_state(player) is None


class TestScoringExports:
    """Smoke test that the scoring entrypoints are importable."""

    def test_score_action_callable(self):
        assert callable(score_action)

    def test_score_valid_actions_callable(self):
        assert callable(score_valid_actions)