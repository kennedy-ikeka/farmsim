"""Tests for `Environment.simulate`."""
from src.domains.environment.environment import Environment
from src.models.player import PlayerConfig
from src.models.resource import ResourceState
from src.models.scoring import ScoredValidStepsState
from src.domains.player.player import Player
from tests.fixtures import _make_env


def _stub_score_valid_actions(valid_steps, player):
    """Empty scored steps — basic_play falls back to all-PASS.

    Used while the scoring module is being rebuilt so the simulate plumbing
    tests don't depend on the (incomplete) `score_action` implementation.
    """
    return ScoredValidStepsState()


class TestSimulate:
    """Tests for `Environment.simulate`."""

    def test_runs_requested_steps(self):
        env = _make_env()
        start_step = env.state.step
        result = env.simulate(steps=3)
        assert env.state.step == start_step + 3
        assert result.done == env.done

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
        result = env.simulate(steps=5)
        assert env.state.step == start
        assert result.done is True

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

    def test_simulate_sets_per_player_states(self, monkeypatch):
        """simulate(player_configs=...) writes each config onto private.config."""
        monkeypatch.setattr(
            "src.domains.player.player.score_valid_actions",
            _stub_score_valid_actions,
        )
        env = _make_env(players=2)
        env.simulate(
            steps=0,
            player_configs=[
                PlayerConfig(method="BASIC", resource_needs=ResourceState(STEP=3.0)),
                PlayerConfig(method="RANDOM", resource_needs=ResourceState(MONEY=5.0)),
            ],
        )
        assert env.state.privates[0].config.method == "BASIC"
        assert env.state.privates[0].config.resource_needs.STEP == 3.0
        assert env.state.privates[1].config.method == "RANDOM"
        assert env.state.privates[1].config.resource_needs.MONEY == 5.0

    def test_simulate_returns_balances_and_winner(self):
        """simulate returns SimulationResultState with balances and winner.

        simulate rebuilds the env via build() (money=3000 for both players);
        with steps=0 no turns run, so both balances stay equal → tie → None.
        """
        env = _make_env(players=2)
        result = env.simulate(steps=0)
        assert set(result.balances.keys()) == {0, 1}
        assert result.winner is None  # tie on equal balances

    def test_simulate_winner_is_highest_balance(self, monkeypatch):
        """Winner is the player id with the highest final balance.

        simulate rebuilds via build() at start, which would wipe any pre-set
        money, so build is patched to a no-op to preserve the skewed balances.
        """
        env = _make_env(players=2)
        monkeypatch.setattr(Environment, "build", lambda self, *a, **kw: None)
        env.state.farms[0].money = 100.0
        env.state.farms[1].money = 500.0
        result = env.simulate(steps=0)
        assert result.balances == {0: 100.0, 1: 500.0}
        assert result.winner == 1

    def test_simulate_winner_none_on_tie(self, monkeypatch):
        """When balances are exactly equal, winner is None."""
        env = _make_env(players=2)
        monkeypatch.setattr(Environment, "build", lambda self, *a, **kw: None)
        env.state.farms[0].money = 300.0
        env.state.farms[1].money = 300.0
        result = env.simulate(steps=0)
        assert result.winner is None

    def test_step_uses_per_player_config_from_privates(self, monkeypatch):
        """Environment.step builds Player views that read config from private.

        Each player's `method` and `resource_needs` travel on
        `state.privates[p].config`; step() passes the private into the
        Player view, which reads `self.private.config` for play dispatch
        and scoring. Patches `Player.__init__` to capture the `private`
        kwarg and checks each view got the right config.
        """
        monkeypatch.setattr(
            "src.domains.player.player.score_valid_actions",
            _stub_score_valid_actions,
        )
        env = _make_env(players=2)
        env.state.privates[0].config = PlayerConfig(
            method="BASIC", resource_needs=ResourceState(STEP=3.0)
        )
        env.state.privates[1].config = PlayerConfig(
            method="RANDOM", resource_needs=ResourceState(MONEY=5.0)
        )

        captured = []
        real_init = Player.__init__

        def spy_init(self, *args, **kwargs):
            priv = kwargs.get("private")
            captured.append({
                "player": kwargs.get("player"),
                "method": priv.config.method,
                "weights": priv.config.resource_needs.model_copy(),
            })
            return real_init(self, *args, **kwargs)

        monkeypatch.setattr(Player, "__init__", spy_init)
        env.step()

        by_player = {c["player"]: c for c in captured}
        assert by_player[0]["method"] == "BASIC"
        assert by_player[0]["weights"].STEP == 3.0
        assert by_player[1]["method"] == "RANDOM"
        assert by_player[1]["weights"].MONEY == 5.0

    def test_step_defaults_player_config_when_unset(self, monkeypatch):
        """A private whose config was never touched keeps PlayerConfig() defaults."""
        monkeypatch.setattr(
            "src.domains.player.player.score_valid_actions",
            _stub_score_valid_actions,
        )
        env = _make_env(players=2)
        # Override only player 0; player 1 stays at the default PlayerConfig().
        env.state.privates[0].config = PlayerConfig(
            method="BASIC", resource_needs=ResourceState(STEP=3.0)
        )

        captured = []
        real_init = Player.__init__

        def spy_init(self, *args, **kwargs):
            priv = kwargs.get("private")
            captured.append({
                "player": kwargs.get("player"),
                "method": priv.config.method,
            })
            return real_init(self, *args, **kwargs)

        monkeypatch.setattr(Player, "__init__", spy_init)
        env.step()

        by_player = {c["player"]: c for c in captured}
        assert by_player[0]["method"] == "BASIC"
        assert by_player[1]["method"] == "RANDOM"  # PlayerConfig() default

    def test_simulate_runs_basic_play_end_to_end(self):
        """simulate with BASIC players exercises the real score_action path.

        Regression guard: `Environment.step` reconstructs Player views from a
        JSON dump, so the views carry plain `FarmState` / `MarketState` (not
        the `Farm` / `Market` controllers). `apply_action` must re-wrap them
        so `Farm.apply` / `Market.apply` exist when scoring. Without the
        re-wrap this raises `AttributeError: 'FarmState' object has no
        attribute 'apply'`.
        """
        env = _make_env(players=2)
        result = env.simulate(
            steps=4,
            player_configs=[
                PlayerConfig(method="BASIC", resource_needs=ResourceState(MONEY=1.0)),
                PlayerConfig(method="RANDOM"),
            ],
        )
        # Both players completed 4 steps without raising.
        assert set(result.balances.keys()) == {0, 1}
        assert result.done is False