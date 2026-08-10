import pytest

from tests.fixtures import _make_env
from src.domains.farm.feed import feed
from src.models.action import FeedActionState
from src.models.environment import StepState
from src.models.farm import AnimalState, PlantState, WeedState


def _structure(kind="COOP", animal="GOOSE", fed_today=False, consecutive_unfed=0):
    return AnimalState(
        kind=kind, animal=animal, fed_today=fed_today, consecutive_unfed=consecutive_unfed,
    )


@pytest.mark.parametrize("kind, animal", [
    ("COOP", "GOOSE"),
    ("PASTURE", "COW"),
    ("PASTURE", "SHEEP"),
])
def test_feed_consumes_wheat_and_marks_fed(kind, animal):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure(kind=kind, animal=animal, consecutive_unfed=2)
    env.state.private.shed.WHEAT = 3

    feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

    tile = farm.tiles[5][5]
    assert tile.fed_today is True
    assert tile.consecutive_unfed == 0
    assert env.state.private.shed.WHEAT == 2


def test_feed_noop_when_already_fed_today():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure(fed_today=True)
    env.state.private.shed.WHEAT = 3

    feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

    assert farm.tiles[5][5].fed_today is True
    assert env.state.private.shed.WHEAT == 3  # not consumed


def test_feed_noop_when_no_wheat_in_shed():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure()
    env.state.private.shed.WHEAT = 0

    feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

    assert farm.tiles[5][5].fed_today is False
    assert env.state.private.shed.WHEAT == 0


def test_feed_noop_on_empty_structure():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = AnimalState(kind="COOP", animal=None)
    env.state.private.shed.WHEAT = 3

    feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

    assert farm.tiles[5][5].fed_today is False
    assert env.state.private.shed.WHEAT == 3  # not consumed


def test_feed_noop_on_non_structure_tile():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120)
    env.state.private.shed.WHEAT = 3

    feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

    assert env.state.private.shed.WHEAT == 3  # not consumed


def test_feed_noop_on_empty_tile():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    env.state.private.shed.WHEAT = 3

    feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

    assert farm.tiles[5][5] is None
    assert env.state.private.shed.WHEAT == 3


@pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
def test_feed_noop_on_malformed_or_negative_position(bad_pos):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure()
    env.state.private.shed.WHEAT = 3
    pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos

    feed(env.state, farm, pos, FeedActionState(type="FEED"))

    assert farm.tiles[5][5].fed_today is False
    assert env.state.private.shed.WHEAT == 3


def test_feed_noop_out_of_bounds():
    env = _make_env(rows=5, cols=5, farmer=(4, 4))
    farm = env.state.farms[0]
    farm.tiles[4][4] = _structure()
    env.state.private.shed.WHEAT = 3

    feed(env.state, farm, [5, 0], FeedActionState(type="FEED"))

    assert farm.tiles[4][4].fed_today is False
    assert env.state.private.shed.WHEAT == 3


def test_step_dispatches_feed():
    env = _make_env(farmer=(3, 3))
    farm = env.state.farms[0]
    farm.tiles[3][3] = _structure(kind="COOP", animal="GOOSE")
    env.state.private.shed.WHEAT = 2

    step = StepState(
        farmer=FeedActionState(type="FEED"),
        hands=[],
        market=[],
    )
    env.step(step)

    assert env.state.farms[0].tiles[3][3].fed_today is True
    assert env.state.private.shed.WHEAT == 1