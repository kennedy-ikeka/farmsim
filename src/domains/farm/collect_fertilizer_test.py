import pytest

from tests.fixtures import _make_env, _play
from src.domains.farm.collect_fertilizer import collect_fertilizer, get_valid_collect_fertilizer_actions_for
from src.models.action import CollectFertilizerActionState
from src.models.environment import StepState
from src.models.farm import AnimalState, WeedState


def _structure(kind="COOP", animal="GOOSE", fertilizer_available=0):
    return AnimalState(
        kind=kind, animal=animal, fertilizer_available=fertilizer_available,
    )


class TestCollectFertilizer:
    """Tests for `collect_fertilizer`."""

    @pytest.mark.parametrize("kind, animal", [
        ("COOP", "GOOSE"),
        ("PASTURE", "COW"),
        ("PASTURE", "SHEEP"),
    ])
    def test_takes_available_to_shed(self, kind, animal):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = _structure(kind=kind, animal=animal, fertilizer_available=1)
        env.state.privates[0].shed.FERTILIZER = 2

        collect_fertilizer(env.state, farm, farm.farmer,
                           CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

        assert farm.tiles[5][5].fertilizer_available == 0
        assert env.state.privates[0].shed.FERTILIZER == 3

    def test_noop_when_none_available(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = _structure(fertilizer_available=0)
        env.state.privates[0].shed.FERTILIZER = 2

        collect_fertilizer(env.state, farm, farm.farmer,
                           CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

        assert farm.tiles[5][5].fertilizer_available == 0
        assert env.state.privates[0].shed.FERTILIZER == 2  # unchanged

    def test_noop_on_empty_structure(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = AnimalState(kind="COOP", animal=None, fertilizer_available=1)
        env.state.privates[0].shed.FERTILIZER = 2

        collect_fertilizer(env.state, farm, farm.farmer,
                           CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

        assert farm.tiles[5][5].fertilizer_available == 1  # not collected
        assert env.state.privates[0].shed.FERTILIZER == 2

    def test_noop_on_non_structure_tile(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = WeedState()
        env.state.privates[0].shed.FERTILIZER = 2

        collect_fertilizer(env.state, farm, farm.farmer,
                           CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

        assert isinstance(farm.tiles[5][5], WeedState)
        assert env.state.privates[0].shed.FERTILIZER == 2

    def test_noop_on_empty_tile(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        env.state.privates[0].shed.FERTILIZER = 2

        collect_fertilizer(env.state, farm, farm.farmer,
                           CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

        assert farm.tiles[5][5] is None
        assert env.state.privates[0].shed.FERTILIZER == 2

    @pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
    def test_noop_on_malformed_or_negative_position(self, bad_pos):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = _structure(fertilizer_available=1)
        env.state.privates[0].shed.FERTILIZER = 2
        pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos

        collect_fertilizer(env.state, farm, pos,
                           CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

        assert farm.tiles[5][5].fertilizer_available == 1
        assert env.state.privates[0].shed.FERTILIZER == 2

    def test_noop_out_of_bounds(self):
        env = _make_env(rows=5, cols=5, farmer=(4, 4))
        farm = env.state.farms[0]
        farm.tiles[4][4] = _structure(fertilizer_available=1)
        env.state.privates[0].shed.FERTILIZER = 2

        collect_fertilizer(env.state, farm, [5, 0],
                           CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

        assert farm.tiles[4][4].fertilizer_available == 1
        assert env.state.privates[0].shed.FERTILIZER == 2


class TestCollectFertilizerDispatch:
    """Integration: collect_fertilizer actions dispatched through `Environment.step` reach `collect_fertilizer`."""

    def test_dispatches_collect_fertilizer(self):
        env = _make_env(farmer=(3, 3))
        farm = env.state.farms[0]
        farm.tiles[3][3] = _structure(kind="PASTURE", animal="COW", fertilizer_available=1)
        env.state.privates[0].shed.FERTILIZER = 0

        step = StepState(
            farmer=CollectFertilizerActionState(type="COLLECT_FERTILIZER"),
            hands=[],
            market=[],
        )
        _play(env, step)

        assert env.state.farms[0].tiles[3][3].fertilizer_available == 0
        assert env.state.privates[0].shed.FERTILIZER == 1


class TestGetValidCollectFertilizerActionsFor:
    """Tests for `get_valid_collect_fertilizer_actions_for`."""

    @pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0]])
    def test_malformed_position_returns_empty(self, bad_pos):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        assert get_valid_collect_fertilizer_actions_for(farm, bad_pos) == []

    def test_out_of_bounds_returns_empty(self):
        env = _make_env(rows=5, cols=5, farmer=(4, 4))
        farm = env.state.farms[0]
        assert get_valid_collect_fertilizer_actions_for(farm, [5, 0]) == []

    def test_empty_tile_returns_empty(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        assert get_valid_collect_fertilizer_actions_for(farm, [5, 5]) == []

    def test_empty_structure_returns_empty(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = AnimalState(kind="COOP", animal=None, fertilizer_available=1)
        assert get_valid_collect_fertilizer_actions_for(farm, [5, 5]) == []

    def test_occupied_coop_no_fertilizer_returns_empty(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = _structure(kind="COOP", animal="GOOSE", fertilizer_available=0)
        assert get_valid_collect_fertilizer_actions_for(farm, [5, 5]) == []

    def test_occupied_coop_with_fertilizer_returns_action(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = _structure(kind="COOP", animal="GOOSE", fertilizer_available=1)
        actions = get_valid_collect_fertilizer_actions_for(farm, [5, 5])
        assert len(actions) == 1
        assert isinstance(actions[0], CollectFertilizerActionState)
        assert actions[0].type == "COLLECT_FERTILIZER"