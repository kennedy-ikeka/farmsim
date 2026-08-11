import pytest

from tests.fixtures import _make_env, _turn
from src.domains.farm.collect_fertilizer import collect_fertilizer
from src.models.action import CollectFertilizerActionState
from src.models.environment import StepState
from src.models.farm import AnimalState, WeedState


def _structure(kind="COOP", animal="GOOSE", fertilizer_available=0):
    return AnimalState(
        kind=kind, animal=animal, fertilizer_available=fertilizer_available,
    )


@pytest.mark.parametrize("kind, animal", [
    ("COOP", "GOOSE"),
    ("PASTURE", "COW"),
    ("PASTURE", "SHEEP"),
])
def test_collect_fertilizer_takes_available_to_shed(kind, animal):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure(kind=kind, animal=animal, fertilizer_available=1)
    env.state.privates[0].shed.FERTILIZER = 2

    collect_fertilizer(env.state, farm, farm.farmer,
                       CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

    assert farm.tiles[5][5].fertilizer_available == 0
    assert env.state.privates[0].shed.FERTILIZER == 3


def test_collect_fertilizer_noop_when_none_available():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure(fertilizer_available=0)
    env.state.privates[0].shed.FERTILIZER = 2

    collect_fertilizer(env.state, farm, farm.farmer,
                       CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

    assert farm.tiles[5][5].fertilizer_available == 0
    assert env.state.privates[0].shed.FERTILIZER == 2  # unchanged


def test_collect_fertilizer_noop_on_empty_structure():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = AnimalState(kind="COOP", animal=None, fertilizer_available=1)
    env.state.privates[0].shed.FERTILIZER = 2

    collect_fertilizer(env.state, farm, farm.farmer,
                       CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

    assert farm.tiles[5][5].fertilizer_available == 1  # not collected
    assert env.state.privates[0].shed.FERTILIZER == 2


def test_collect_fertilizer_noop_on_non_structure_tile():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = WeedState()
    env.state.privates[0].shed.FERTILIZER = 2

    collect_fertilizer(env.state, farm, farm.farmer,
                       CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

    assert isinstance(farm.tiles[5][5], WeedState)
    assert env.state.privates[0].shed.FERTILIZER == 2


def test_collect_fertilizer_noop_on_empty_tile():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    env.state.privates[0].shed.FERTILIZER = 2

    collect_fertilizer(env.state, farm, farm.farmer,
                       CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

    assert farm.tiles[5][5] is None
    assert env.state.privates[0].shed.FERTILIZER == 2


@pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
def test_collect_fertilizer_noop_on_malformed_or_negative_position(bad_pos):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure(fertilizer_available=1)
    env.state.privates[0].shed.FERTILIZER = 2
    pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos

    collect_fertilizer(env.state, farm, pos,
                       CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

    assert farm.tiles[5][5].fertilizer_available == 1
    assert env.state.privates[0].shed.FERTILIZER == 2


def test_collect_fertilizer_noop_out_of_bounds():
    env = _make_env(rows=5, cols=5, farmer=(4, 4))
    farm = env.state.farms[0]
    farm.tiles[4][4] = _structure(fertilizer_available=1)
    env.state.privates[0].shed.FERTILIZER = 2

    collect_fertilizer(env.state, farm, [5, 0],
                       CollectFertilizerActionState(type="COLLECT_FERTILIZER"))

    assert farm.tiles[4][4].fertilizer_available == 1
    assert env.state.privates[0].shed.FERTILIZER == 2


def test_step_dispatches_collect_fertilizer():
    env = _make_env(farmer=(3, 3))
    farm = env.state.farms[0]
    farm.tiles[3][3] = _structure(kind="PASTURE", animal="COW", fertilizer_available=1)
    env.state.privates[0].shed.FERTILIZER = 0

    step = StepState(
        farmer=CollectFertilizerActionState(type="COLLECT_FERTILIZER"),
        hands=[],
        market=[],
    )
    env.step(_turn(step))

    assert env.state.farms[0].tiles[3][3].fertilizer_available == 0
    assert env.state.privates[0].shed.FERTILIZER == 1