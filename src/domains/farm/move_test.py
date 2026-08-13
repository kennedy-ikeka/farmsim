import pytest

from tests.fixtures import _make_env, _play
from src.domains.farm.move import _MOVE_DELTAS, get_valid_move_actions_for, move_unit
from src.models.action import MoveActionState, PassActionState
from src.models.environment import StepState
from src.models.farm import FarmState


def _types(actions):
    return sorted(a.type for a in actions)


class TestMoveUnit:
    """Tests for `move_unit`."""

    @pytest.mark.parametrize(
        "direction, expected",
        [
            ("NORTH", [4, 5]),
            ("SOUTH", [6, 5]),
            ("EAST", [5, 6]),
            ("WEST", [5, 4]),
        ],
    )
    def test_each_direction_from_center(self, direction, expected):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        pos = farm.farmer
        move_unit(farm, pos, direction)
        assert pos == expected

    def test_returns_occurred_dict(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        result = move_unit(farm, farm.farmer, "NORTH")
        assert result == {"from": [5, 5], "to": [4, 5], "moved": True}

    def test_mutates_in_place(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        pos = farm.farmer
        original_id = id(pos)
        move_unit(farm, pos, "NORTH")
        assert id(farm.farmer) == original_id  # same list object
        assert pos is farm.farmer

    @pytest.mark.parametrize(
        "start, direction, expected",
        [
            # top edge
            ([0, 5], "NORTH", [0, 5]),
            # bottom edge
            ([9, 5], "SOUTH", [9, 5]),
            # left edge
            ([5, 0], "WEST", [5, 0]),
            # right edge
            ([5, 9], "EAST", [5, 9]),
            # corners — outward moves on both axes
            ([0, 0], "NORTH", [0, 0]),
            ([0, 0], "WEST", [0, 0]),
            ([9, 9], "SOUTH", [9, 9]),
            ([9, 9], "EAST", [9, 9]),
            ([0, 9], "NORTH", [0, 9]),
            ([0, 9], "EAST", [0, 9]),
            ([9, 0], "SOUTH", [9, 0]),
            ([9, 0], "WEST", [9, 0]),
        ],
    )
    def test_clamps_at_bounds(self, start, direction, expected):
        rows, cols = 10, 10
        tiles = [[None] * cols for _ in range(rows)]
        farm = FarmState(
            money=0.0, tiles=tiles, farmer=list(start),
            hands=[], unlocked_quadrants=["NW"], hires_today=0,
        )
        env = _make_env()
        env.state.farms[0] = farm
        move_unit(farm, farm.farmer, direction)
        assert farm.farmer == expected

    def test_can_reach_each_corner_from_center(self):
        """A sequence of moves should be able to reach every corner without escaping."""
        env = _make_env(rows=5, cols=5, farmer=(2, 2))
        farm = env.state.farms[0]
        # go NW
        for _ in range(2):
            move_unit(farm, farm.farmer, "NORTH")
            move_unit(farm, farm.farmer, "WEST")
        assert farm.farmer == [0, 0]
        # go SE
        for _ in range(4):
            move_unit(farm, farm.farmer, "SOUTH")
            move_unit(farm, farm.farmer, "EAST")
        assert farm.farmer == [4, 4]
        # further moves clamp
        move_unit(farm, farm.farmer, "SOUTH")
        move_unit(farm, farm.farmer, "EAST")
        assert farm.farmer == [4, 4]

    def test_bounds_derived_from_tiles_non_square(self):
        env = _make_env(rows=4, cols=8, farmer=(3, 7))
        farm = env.state.farms[0]
        # at bottom-right corner of a 4x8 grid
        move_unit(farm, farm.farmer, "SOUTH")
        assert farm.farmer == [3, 7]  # row 3 is the last valid row
        move_unit(farm, farm.farmer, "EAST")
        assert farm.farmer == [3, 7]  # col 7 is the last valid col
        move_unit(farm, farm.farmer, "NORTH")
        assert farm.farmer == [2, 7]
        move_unit(farm, farm.farmer, "WEST")
        assert farm.farmer == [2, 6]

    def test_small_grid_clamps_at_size_minus_one(self):
        env = _make_env(rows=3, cols=3, farmer=(2, 2))
        farm = env.state.farms[0]
        move_unit(farm, farm.farmer, "SOUTH")
        move_unit(farm, farm.farmer, "EAST")
        assert farm.farmer == [2, 2]

    def test_can_move_onto_locked_tile(self):
        """AGENTS.md: units can cross unbought (LOCKED) quadrants; only bounds apply."""
        tiles = [[None] * 10 for _ in range(10)]
        tiles[4][5] = "LOCKED"  # the destination of a NORTH move from [5,5]
        env = _make_env(farmer=(5, 5), tiles=tiles)
        farm = env.state.farms[0]
        move_unit(farm, farm.farmer, "NORTH")
        assert farm.farmer == [4, 5]  # moved onto the LOCKED tile

    @pytest.mark.parametrize("bad_pos", [None, (5, 5), [5], [], [5, 5, 0], "5,5"])
    def test_ignores_non_two_element_list_positions(self, bad_pos):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        pos = list(bad_pos) if isinstance(bad_pos, (list, tuple)) and not isinstance(bad_pos, str) else bad_pos
        # Should not raise and should not mutate `pos` meaningfully.
        move_unit(farm, pos, "NORTH")
        # The farm's actual farmer position is untouched because we passed a bogus pos.
        assert farm.farmer == [5, 5]

    def test_ignores_unknown_direction(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        move_unit(farm, farm.farmer, "TELEPORT")
        assert farm.farmer == [5, 5]  # unchanged

    def test_delta_table_conventions(self):
        """NORTH decrements row, SOUTH increments row, EAST increments col, WEST decrements col."""
        assert _MOVE_DELTAS == {
            "NORTH": (-1, 0),
            "SOUTH": (1, 0),
            "EAST": (0, 1),
            "WEST": (0, -1),
        }


class TestGetValidMoveActionsFor:
    """Tests for `get_valid_move_actions_for`.

    A move is valid iff playing it via `move_unit` would move the unit
    (moved=True); the only nullifying case is going off-grid, since locked
    tiles are passable.
    """

    def test_center_returns_all_four(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        assert _types(get_valid_move_actions_for(farm, farm.farmer)) == ["EAST", "NORTH", "SOUTH", "WEST"]

    @pytest.mark.parametrize(
        "pos, excluded",
        [
            ([0, 5], "NORTH"),   # top edge
            ([9, 5], "SOUTH"),   # bottom edge
            ([5, 0], "WEST"),    # left edge
            ([5, 9], "EAST"),    # right edge
        ],
    )
    def test_edge_excludes_off_grid_direction(self, pos, excluded):
        env = _make_env(rows=10, cols=10)
        farm = env.state.farms[0]
        valid = _types(get_valid_move_actions_for(farm, pos))
        assert excluded not in valid
        assert sorted(["NORTH", "SOUTH", "EAST", "WEST"]) == sorted(valid + [excluded])

    @pytest.mark.parametrize(
        "pos, expected",
        [
            ([0, 0], ["EAST", "SOUTH"]),
            ([0, 9], ["SOUTH", "WEST"]),
            ([9, 0], ["EAST", "NORTH"]),
            ([9, 9], ["NORTH", "WEST"]),
        ],
    )
    def test_corner_keeps_only_two(self, pos, expected):
        env = _make_env(rows=10, cols=10)
        farm = env.state.farms[0]
        assert _types(get_valid_move_actions_for(farm, pos)) == sorted(expected)

    def test_works_for_hand_positions(self):
        """Hands are moved via the same move_unit, so they must be validated too."""
        env = _make_env(farmer=(5, 5), hands=[[0, 0], [9, 9]])
        farm = env.state.farms[0]
        assert _types(get_valid_move_actions_for(farm, farm.hands[0])) == ["EAST", "SOUTH"]
        assert _types(get_valid_move_actions_for(farm, farm.hands[1])) == ["NORTH", "WEST"]

    def test_locked_destination_is_valid(self):
        """Locked tiles are passable — a move onto a LOCKED tile is not a no-op."""
        tiles = [[None] * 10 for _ in range(10)]
        tiles[4][5] = "LOCKED"  # NORTH destination from [5,5]
        env = _make_env(farmer=(5, 5), tiles=tiles)
        farm = env.state.farms[0]
        assert "NORTH" in _types(get_valid_move_actions_for(farm, farm.farmer))

    def test_bounds_derived_from_non_square_grid(self):
        env = _make_env(rows=4, cols=8, farmer=(3, 7))
        farm = env.state.farms[0]
        # bottom-right of a 4x8 grid: only NORTH and WEST keep the unit in bounds
        assert _types(get_valid_move_actions_for(farm, farm.farmer)) == ["NORTH", "WEST"]

    @pytest.mark.parametrize("bad_pos", [None, (5, 5), [5], [], [5, 5, 0], "5,5"])
    def test_ignores_malformed_positions(self, bad_pos):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        assert get_valid_move_actions_for(farm, bad_pos) == []

    @pytest.mark.parametrize("farmer_pos", [[5, 5], [0, 0], [9, 9], [0, 9], [9, 0]])
    def test_every_returned_move_actually_moves_the_unit(self, farmer_pos):
        """Core 'not nullified' property: each valid action, when played via
        move_unit from the same position, must return moved=True (and not just
        be a silently-clamped no-op)."""
        env = _make_env(farmer=tuple(farmer_pos))
        farm = env.state.farms[0]
        for action in get_valid_move_actions_for(farm, list(farmer_pos)):
            probe = list(farmer_pos)
            result = move_unit(farm, probe, action.type)
            assert result["moved"] is True, f"{action.type} from {farmer_pos} was not a real move"


class TestMoveDispatch:
    """Integration: move actions dispatched through `Environment.step` reach `move_unit`."""

    @pytest.mark.parametrize(
        "direction, expected",
        [
            ("NORTH", [4, 5]),
            ("SOUTH", [6, 5]),
            ("EAST", [5, 6]),
            ("WEST", [5, 4]),
        ],
    )
    def test_dispatches_move_action_to_farmer(self, direction, expected):
        env = _make_env(farmer=(5, 5))
        step = StepState(farmer=MoveActionState(type=direction), hands=[], market=[])
        _play(env, step)
        assert env.state.farms[0].farmer == expected

    def test_pass_leaves_farmer_in_place(self):
        env = _make_env(farmer=(5, 5))
        step = StepState(farmer=PassActionState(type="PASS"), hands=[], market=[])
        _play(env, step)
        assert env.state.farms[0].farmer == [5, 5]

    def test_clamps_farmer_at_edge(self):
        env = _make_env(farmer=(0, 0))
        step = StepState(farmer=MoveActionState(type="NORTH"), hands=[], market=[])
        _play(env, step)
        assert env.state.farms[0].farmer == [0, 0]