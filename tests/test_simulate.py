"""Tests for `Environment.simulate`."""
from src.domains.environment.environment import Environment
from src.models.environment import TurnActions
from tests.fixtures import _make_env


def test_simulate_runs_requested_steps():
    env = _make_env()
    start_step = env.state.step
    env.simulate(steps=3)
    assert env.state.step == start_step + 3


def test_simulate_builds_one_player_per_private():
    env = _make_env(players=2)
    assert len(env.state.privates) == 2
    env.simulate(steps=1)
    # step() dispatched actions for both players → events non-empty.
    assert env.events


def test_simulate_stops_when_done():
    env = _make_env()
    env.done = True
    start = env.state.step
    env.simulate(steps=5)
    assert env.state.step == start


def test_simulate_passes_per_player_actions(monkeypatch):
    env = _make_env(players=2)
    captured = []
    real_step = Environment.step

    def spy(self, payload: TurnActions):
        captured.append(len(payload.actions))
        return real_step(self, payload)

    monkeypatch.setattr(Environment, "step", spy)
    env.simulate(steps=2)
    assert captured == [2, 2]