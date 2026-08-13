"""Tests for `Environment.simulate`."""
from src.domains.environment.environment import Environment
from tests.fixtures import _make_env


class TestSimulate:
    """Tests for `Environment.simulate`."""

    def test_runs_requested_steps(self):
        env = _make_env()
        start_step = env.state.step
        env.simulate(steps=3)
        assert env.state.step == start_step + 3

    def test_builds_one_player_per_private(self):
        env = _make_env(players=2)
        assert len(env.state.privates) == 2
        env.simulate(steps=1)
        # step() dispatched actions for both players → events non-empty.
        assert env.events

    def test_stops_when_done(self):
        env = _make_env()
        env.done = True
        start = env.state.step
        env.simulate(steps=5)
        assert env.state.step == start

    def test_calls_step_once_per_step(self, monkeypatch):
        """simulate(steps=N) invokes Environment.step exactly N times."""
        env = _make_env(players=2)
        calls = []
        real_step = Environment.step

        def spy(self):
            calls.append(None)
            return real_step(self)

        monkeypatch.setattr(Environment, "step", spy)
        env.simulate(steps=2)
        assert len(calls) == 2