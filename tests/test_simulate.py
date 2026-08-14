"""Tests for `Environment.simulate`."""
from src.domains.environment.environment import Environment
from src.models.player import PlayerConfig
from src.models.resource_weights import ResourceWeights
from src.domains.player.player import Player
from tests.fixtures import _make_env


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

    def test_simulate_sets_per_player_states(self):
        """simulate(player_configs=...) writes each config onto private.config."""
        env = _make_env(players=2)
        env.simulate(
            steps=0,
            player_configs=[
                PlayerConfig(method="BEST_CHOISE", resource_weights=ResourceWeights(STEP=3.0)),
                PlayerConfig(method="TACTICAL", resource_weights=ResourceWeights(MONEY=5.0)),
            ],
        )
        assert env.state.privates[0].config.method == "BEST_CHOISE"
        assert env.state.privates[0].config.resource_weights.STEP == 3.0
        assert env.state.privates[1].config.method == "TACTICAL"
        assert env.state.privates[1].config.resource_weights.MONEY == 5.0

    def test_simulate_returns_balances_and_winner(self):
        """simulate returns SimulationResultState with balances and winner."""
        env = _make_env(players=2)
        # Both start with 0 money → tie → winner is None.
        result = env.simulate(steps=1)
        assert set(result.balances.keys()) == {0, 1}
        assert result.winner is None  # tie on equal balances

    def test_simulate_winner_is_highest_balance(self, monkeypatch):
        """Winner is the player id with the highest final balance."""
        env = _make_env(players=2)
        env.step()  # run a turn so state has farms
        # Skew balances: player 1 ends richer.
        env.state.farms[0].money = 100.0
        env.state.farms[1].money = 500.0
        result = env.simulate(steps=0)
        assert result.balances == {0: 100.0, 1: 500.0}
        assert result.winner == 1

    def test_simulate_winner_none_on_tie(self):
        """When balances are exactly equal, winner is None."""
        env = _make_env(players=2)
        env.state.farms[0].money = 300.0
        env.state.farms[1].money = 300.0
        result = env.simulate(steps=0)
        assert result.winner is None

    def test_step_uses_per_player_config_from_privates(self, monkeypatch):
        """Environment.step builds Player views that read config from private.

        Each player's `method` and `resource_weights` travel on
        `state.privates[p].config`; step() passes the private into the
        Player view, which reads `self.private.config` for play dispatch
        and scoring. Patches `Player.__init__` to capture the `private`
        kwarg and checks each view got the right config.
        """
        env = _make_env(players=2)
        env.state.privates[0].config = PlayerConfig(
            method="BEST_CHOISE", resource_weights=ResourceWeights(STEP=3.0)
        )
        env.state.privates[1].config = PlayerConfig(
            method="TACTICAL", resource_weights=ResourceWeights(MONEY=5.0)
        )

        captured = []
        real_init = Player.__init__

        def spy_init(self, *args, **kwargs):
            priv = kwargs.get("private")
            captured.append({
                "player": kwargs.get("player"),
                "method": priv.config.method,
                "weights": priv.config.resource_weights,
            })
            return real_init(self, *args, **kwargs)

        monkeypatch.setattr(Player, "__init__", spy_init)
        env.step()

        by_player = {c["player"]: c for c in captured}
        assert by_player[0]["method"] == "BEST_CHOISE"
        assert by_player[0]["weights"].STEP == 3.0
        assert by_player[1]["method"] == "TACTICAL"
        assert by_player[1]["weights"].MONEY == 5.0

    def test_step_defaults_player_config_when_unset(self, monkeypatch):
        """A private whose config was never touched keeps PlayerConfig() defaults."""
        env = _make_env(players=2)
        # Override only player 0; player 1 stays at the default PlayerConfig().
        env.state.privates[0].config = PlayerConfig(
            method="BEST_CHOISE", resource_weights=ResourceWeights(STEP=3.0)
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
        assert by_player[0]["method"] == "BEST_CHOISE"
        assert by_player[1]["method"] == "RANDOM"  # PlayerConfig() default