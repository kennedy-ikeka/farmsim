import pytest

from tests.fixtures import _make_env, _play
from src.domains.farm.build_structure import build_structure, get_valid_build_actions_for
from src.models.action import BuildCoopActionState, BuildPastureActionState
from src.models.environment import StepState
from src.models.farm import AnimalState, PlantState, WeedState


class TestBuildStructure:
    """Tests for `build_structure`."""

    @pytest.mark.parametrize("action_type, kind", [
        ("BUILD_COOP", "COOP"),
        ("BUILD_PASTURE", "PASTURE"),
    ])
    def test_creates_structure_on_empty_tile(self, action_type, kind):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        action_cls = BuildCoopActionState if action_type == "BUILD_COOP" else BuildPastureActionState

        build_structure(farm, farm.farmer, action_cls(type=action_type))

        tile = farm.tiles[5][5]
        assert isinstance(tile, AnimalState)
        assert tile.kind == kind
        assert tile.animal is None  # empty structure

    def test_noop_on_locked_tile(self):
        tiles = [[None] * 10 for _ in range(10)]
        tiles[5][5] = "LOCKED"
        env = _make_env(farmer=(5, 5), tiles=tiles)
        farm = env.state.farms[0]

        build_structure(farm, farm.farmer, BuildCoopActionState(type="BUILD_COOP"))

        assert farm.tiles[5][5] == "LOCKED"

    @pytest.mark.parametrize("occupant", [
        PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120),
        WeedState(),
        AnimalState(kind="COOP"),
    ])
    def test_noop_on_occupied_tile(self, occupant):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = occupant

        build_structure(farm, farm.farmer, BuildCoopActionState(type="BUILD_COOP"))

        assert isinstance(farm.tiles[5][5], type(occupant))  # original preserved

    def test_noop_on_existing_structure_preserves_it(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = AnimalState(kind="PASTURE", animal="COW")

        build_structure(farm, farm.farmer, BuildCoopActionState(type="BUILD_COOP"))

        tile = farm.tiles[5][5]
        assert isinstance(tile, AnimalState)
        assert tile.kind == "PASTURE"  # unchanged
        assert tile.animal == "COW"

    @pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
    def test_noop_on_malformed_or_negative_position(self, bad_pos):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos
        build_structure(farm, pos, BuildCoopActionState(type="BUILD_COOP"))
        assert farm.tiles[5][5] is None

    def test_noop_out_of_bounds(self):
        env = _make_env(rows=5, cols=5, farmer=(4, 4))
        farm = env.state.farms[0]
        build_structure(farm, [5, 0], BuildCoopActionState(type="BUILD_COOP"))
        for row in farm.tiles:
            assert all(t is None for t in row)


class TestBuildStructureDispatch:
    """Integration: build actions dispatched through `Environment.step` reach `build_structure`."""

    def test_dispatches_build_coop(self):
        env = _make_env(farmer=(3, 3))
        step = StepState(
            farmer=BuildCoopActionState(type="BUILD_COOP"),
            hands=[],
            market=[],
        )
        _play(env, step)
        tile = env.state.farms[0].tiles[3][3]
        assert isinstance(tile, AnimalState)
        assert tile.kind == "COOP"
        assert tile.animal is None

    def test_dispatches_build_pasture(self):
        env = _make_env(farmer=(3, 3))
        step = StepState(
            farmer=BuildPastureActionState(type="BUILD_PASTURE"),
            hands=[],
            market=[],
        )
        _play(env, step)
        tile = env.state.farms[0].tiles[3][3]
        assert isinstance(tile, AnimalState)
        assert tile.kind == "PASTURE"


class TestGetValidBuildActionsFor:
    """Tests for `get_valid_build_actions_for`."""

    @pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0]])
    def test_malformed_position_returns_empty(self, bad_pos):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        assert get_valid_build_actions_for(farm, bad_pos) == []

    def test_out_of_bounds_returns_empty(self):
        env = _make_env(rows=5, cols=5, farmer=(4, 4))
        farm = env.state.farms[0]
        assert get_valid_build_actions_for(farm, [5, 0]) == []

    def test_empty_tile_returns_both_builds(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        actions = get_valid_build_actions_for(farm, [5, 5])
        assert len(actions) == 2
        types = sorted(a.type for a in actions)
        assert types == ["BUILD_COOP", "BUILD_PASTURE"]
        assert isinstance(actions[0], (BuildCoopActionState, BuildPastureActionState))
        assert isinstance(actions[1], (BuildCoopActionState, BuildPastureActionState))

    def test_locked_tile_returns_empty(self):
        tiles = [[None] * 10 for _ in range(10)]
        tiles[5][5] = "LOCKED"
        env = _make_env(farmer=(5, 5), tiles=tiles)
        farm = env.state.farms[0]
        assert get_valid_build_actions_for(farm, [5, 5]) == []

    def test_plant_tile_returns_empty(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120)
        assert get_valid_build_actions_for(farm, [5, 5]) == []

    def test_existing_structure_returns_empty(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = AnimalState(kind="COOP", animal="GOOSE")
        assert get_valid_build_actions_for(farm, [5, 5]) == []