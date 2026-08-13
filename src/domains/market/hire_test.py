import pytest

from tests.fixtures import _make_env, _play
from src.domains.market.hire import hire, _fib
from src.models.action import HireActionState, PassActionState
from src.models.environment import StepState


class TestFib:
    """Tests for `_fib`."""

    # ---------------------------------------------------------------------------
    # Fibonacci cost sequence — 1, 1, 2, 3, 5, 8, 13, 21, ...
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("n, expected", [
        (0, 1), (1, 1), (2, 2), (3, 3), (4, 5), (5, 8), (6, 13), (7, 21),
    ])
    def test_sequence(self, n, expected):
        assert _fib(n) == expected


class TestHire:
    """Tests for `hire`."""

    # ---------------------------------------------------------------------------
    # Successful hire — deducts cost, increments hires_today, appends a hand.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("hires_so_far, expected_cost", [
        (0, 1), (1, 1), (2, 2), (3, 3), (4, 5), (5, 8),
    ])
    def test_deducts_escalating_cost(self, hires_so_far, expected_cost):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.money = 1000.0
        farm.hires_today = hires_so_far

        hire(env.state, HireActionState(type="HIRE"))

        assert farm.money == 1000.0 - expected_cost
        assert farm.hires_today == hires_so_far + 1
        assert len(farm.hands) == 1

    def test_multiple_times_escalates_cost(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.money = 100.0

        hire(env.state, HireActionState(type="HIRE"))  # cost 1
        hire(env.state, HireActionState(type="HIRE"))  # cost 1
        hire(env.state, HireActionState(type="HIRE"))  # cost 2
        hire(env.state, HireActionState(type="HIRE"))  # cost 3

        assert farm.hires_today == 4
        assert len(farm.hands) == 4
        assert farm.money == 100.0 - (1 + 1 + 2 + 3)

    # ---------------------------------------------------------------------------
    # Hand spawn position — NWSE preference on the four center tiles.
    # ---------------------------------------------------------------------------

    def test_first_hire_spawns_at_sw_center_tile(self):
        """Farmer at (4,4); first free center tile in NWSE order is (5,4)."""
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.money = 100.0

        hire(env.state, HireActionState(type="HIRE"))

        assert farm.hands[0] == [5, 4]

    def test_second_hire_spawns_at_next_free_center_tile(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.money = 100.0

        hire(env.state, HireActionState(type="HIRE"))  # -> (5,4)
        hire(env.state, HireActionState(type="HIRE"))  # -> (4,5)

        assert farm.hands[0] == [5, 4]
        assert farm.hands[1] == [4, 5]

    def test_picks_least_occupied_when_all_center_tiles_occupied(self):
        """When all four center tiles have at least one occupant, the least-
        occupied one is chosen (NWSE tie-break)."""
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.money = 1000.0
        # Pre-occupy all four center tiles.
        farm.hands = [[5, 4], [4, 5], [5, 5]]

        hire(env.state, HireActionState(type="HIRE"))

        # (4,4) has 1 occupant (the farmer); others have 1 each.
        # All have 1, so NWSE tie-break -> (4,4) (first in order).
        assert farm.hands[-1] == [4, 4]

    # ---------------------------------------------------------------------------
    # No-op when the farm cannot afford the hire.
    # ---------------------------------------------------------------------------

    def test_noop_when_cannot_afford(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.money = 0.0

        hire(env.state, HireActionState(type="HIRE"))

        assert farm.hires_today == 0
        assert len(farm.hands) == 0
        assert farm.money == 0.0

    def test_noop_then_affordable_after_earning(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.money = 0.0

        hire(env.state, HireActionState(type="HIRE"))  # no-op
        assert farm.hires_today == 0

        farm.money = 5.0
        hire(env.state, HireActionState(type="HIRE"))  # cost 1
        assert farm.hires_today == 1
        assert farm.money == 4.0


class TestHireDispatch:
    """Integration: hire dispatched through `Environment.step`."""

    def test_dispatches_hire_action(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        farm.money = 50.0

        step = StepState(
            farmer=PassActionState(type="PASS"),
            hands=[],
            market=[HireActionState(type="HIRE")],
        )
        _play(env, step)

        assert farm.hires_today == 1
        assert len(farm.hands) == 1
        assert farm.hands[0] == [5, 4]
        assert farm.money == 49.0