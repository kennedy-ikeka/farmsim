import pytest

from tests.fixtures import _make_env, _turn
from src.domains.farm.move import _MOVE_DELTAS, move_unit
from src.models.action import MoveActionState, PassActionState
from src.models.environment import StepState
from src.models.farm import FarmState


# ---------------------------------------------------------------------------
# Direction correctness from a centre position.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "direction, expected",
    [
        ("NORTH", [4, 5]),
        ("SOUTH", [6, 5]),
        ("EAST", [5, 6]),
        ("WEST", [5, 4]),
    ],
)
def test_move_unit_each_direction_from_center(direction, expected):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    pos = farm.farmer
    move_unit(farm, pos, direction)
    assert pos == expected


def test_move_unit_returns_occurred_dict():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    result = move_unit(farm, farm.farmer, "NORTH")
    assert result == {"from": [5, 5], "to": [4, 5], "moved": True}


def test_move_unit_mutates_in_place():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    pos = farm.farmer
    original_id = id(pos)
    move_unit(farm, pos, "NORTH")
    assert id(farm.farmer) == original_id  # same list object
    assert pos is farm.farmer


# ---------------------------------------------------------------------------
# Edge clamping — out-of-bounds moves are silently ignored.
# ---------------------------------------------------------------------------

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
def test_move_unit_clamps_at_bounds(start, direction, expected):
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


def test_move_unit_can_reach_each_corner_from_center():
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


# ---------------------------------------------------------------------------
# Bounds are derived from the tile grid, not hardcoded.
# ---------------------------------------------------------------------------

def test_move_unit_bounds_derived_from_tiles_non_square():
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


def test_move_unit_small_grid_clamps_at_size_minus_one():
    env = _make_env(rows=3, cols=3, farmer=(2, 2))
    farm = env.state.farms[0]
    move_unit(farm, farm.farmer, "SOUTH")
    move_unit(farm, farm.farmer, "EAST")
    assert farm.farmer == [2, 2]


# ---------------------------------------------------------------------------
# Locked tiles are passable — only grid bounds apply.
# ---------------------------------------------------------------------------

def test_move_unit_can_move_onto_locked_tile():
    """AGENTS.md: units can cross unbought (LOCKED) quadrants; only bounds apply."""
    tiles = [[None] * 10 for _ in range(10)]
    tiles[4][5] = "LOCKED"  # the destination of a NORTH move from [5,5]
    env = _make_env(farmer=(5, 5), tiles=tiles)
    farm = env.state.farms[0]
    move_unit(farm, farm.farmer, "NORTH")
    assert farm.farmer == [4, 5]  # moved onto the LOCKED tile


# ---------------------------------------------------------------------------
# Invalid / malformed positions are silently skipped.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_pos", [None, (5, 5), [5], [], [5, 5, 0], "5,5"])
def test_move_unit_ignores_non_two_element_list_positions(bad_pos):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    pos = list(bad_pos) if isinstance(bad_pos, (list, tuple)) and not isinstance(bad_pos, str) else bad_pos
    # Should not raise and should not mutate `pos` meaningfully.
    move_unit(farm, pos, "NORTH")
    # The farm's actual farmer position is untouched because we passed a bogus pos.
    assert farm.farmer == [5, 5]


def test_move_unit_ignores_unknown_direction():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    move_unit(farm, farm.farmer, "TELEPORT")
    assert farm.farmer == [5, 5]  # unchanged


# ---------------------------------------------------------------------------
# Integration: dispatch through Environment.step() reaches move_unit.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "direction, expected",
    [
        ("NORTH", [4, 5]),
        ("SOUTH", [6, 5]),
        ("EAST", [5, 6]),
        ("WEST", [5, 4]),
    ],
)
def test_step_dispatches_move_action_to_farmer(direction, expected):
    env = _make_env(farmer=(5, 5))
    step = StepState(farmer=MoveActionState(type=direction), hands=[], market=[])
    env.step(_turn(step))
    assert env.state.farms[0].farmer == expected


def test_step_pass_leaves_farmer_in_place():
    env = _make_env(farmer=(5, 5))
    step = StepState(farmer=PassActionState(type="PASS"), hands=[], market=[])
    env.step(_turn(step))
    assert env.state.farms[0].farmer == [5, 5]


def test_step_clamps_farmer_at_edge():
    env = _make_env(farmer=(0, 0))
    step = StepState(farmer=MoveActionState(type="NORTH"), hands=[], market=[])
    env.step(_turn(step))
    assert env.state.farms[0].farmer == [0, 0]


# ---------------------------------------------------------------------------
# Sanity: the move-delta table matches the documented conventions.
# ---------------------------------------------------------------------------

def test_move_delta_table_conventions():
    """NORTH decrements row, SOUTH increments row, EAST increments col, WEST decrements col."""
    assert _MOVE_DELTAS == {
        "NORTH": (-1, 0),
        "SOUTH": (1, 0),
        "EAST": (0, 1),
        "WEST": (0, -1),
    }