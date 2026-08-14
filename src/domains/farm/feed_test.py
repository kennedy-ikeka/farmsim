import pytest

from tests.fixtures import _make_env, _play
from src.domains.farm.feed import feed, get_valid_feed_actions_for
from src.domains.player.player import Player
from src.models.action import FeedActionState
from src.models.environment import StepState
from src.models.farm import AnimalState, PlantState, WeedState


def _structure(kind="COOP", animal="GOOSE", fed_today=False, consecutive_unfed=0):
    return AnimalState(
        kind=kind, animal=animal, fed_today=fed_today, consecutive_unfed=consecutive_unfed,
    )


class TestFeed:
    """Tests for `feed`."""

    @pytest.mark.parametrize("kind, animal", [
        ("COOP", "GOOSE"),
        ("PASTURE", "COW"),
        ("PASTURE", "SHEEP"),
    ])
    def test_consumes_wheat_and_marks_fed(self, kind, animal):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = _structure(kind=kind, animal=animal, consecutive_unfed=2)
        env.state.privates[0].shed.WHEAT = 3

        feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

        tile = farm.tiles[5][5]
        assert tile.fed_today is True
        assert tile.consecutive_unfed == 0
        assert env.state.privates[0].shed.WHEAT == 2

    def test_noop_when_already_fed_today(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = _structure(fed_today=True)
        env.state.privates[0].shed.WHEAT = 3

        feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

        assert farm.tiles[5][5].fed_today is True
        assert env.state.privates[0].shed.WHEAT == 3  # not consumed

    def test_noop_when_no_wheat_in_shed(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = _structure()
        env.state.privates[0].shed.WHEAT = 0

        feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

        assert farm.tiles[5][5].fed_today is False
        assert env.state.privates[0].shed.WHEAT == 0

    def test_noop_on_empty_structure(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = AnimalState(kind="COOP", animal=None)
        env.state.privates[0].shed.WHEAT = 3

        feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

        assert farm.tiles[5][5].fed_today is False
        assert env.state.privates[0].shed.WHEAT == 3  # not consumed

    def test_noop_on_non_structure_tile(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120)
        env.state.privates[0].shed.WHEAT = 3

        feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

        assert env.state.privates[0].shed.WHEAT == 3  # not consumed

    def test_noop_on_empty_tile(self):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 3

        feed(env.state, farm, farm.farmer, FeedActionState(type="FEED"))

        assert farm.tiles[5][5] is None
        assert env.state.privates[0].shed.WHEAT == 3

    @pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
    def test_noop_on_malformed_or_negative_position(self, bad_pos):
        env = _make_env(farmer=(5, 5))
        farm = env.state.farms[0]
        farm.tiles[5][5] = _structure()
        env.state.privates[0].shed.WHEAT = 3
        pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos

        feed(env.state, farm, pos, FeedActionState(type="FEED"))

        assert farm.tiles[5][5].fed_today is False
        assert env.state.privates[0].shed.WHEAT == 3

    def test_noop_out_of_bounds(self):
        env = _make_env(rows=5, cols=5, farmer=(4, 4))
        farm = env.state.farms[0]
        farm.tiles[4][4] = _structure()
        env.state.privates[0].shed.WHEAT = 3

        feed(env.state, farm, [5, 0], FeedActionState(type="FEED"))

        assert farm.tiles[4][4].fed_today is False
        assert env.state.privates[0].shed.WHEAT == 3


class TestFeedDispatch:
    """Integration: feed actions dispatched through `Environment.step` reach `feed`."""

    def test_dispatches_feed(self):
        env = _make_env(farmer=(3, 3))
        farm = env.state.farms[0]
        farm.tiles[3][3] = _structure(kind="COOP", animal="GOOSE")
        env.state.privates[0].shed.WHEAT = 2

        step = StepState(
            farmer=FeedActionState(type="FEED"),
            hands=[],
            market=[],
        )
        _play(env, step)

        assert env.state.farms[0].tiles[3][3].fed_today is True
        assert env.state.privates[0].shed.WHEAT == 1


class TestGetValidFeedActionsFor:
    """Tests for `get_valid_feed_actions_for`."""

    @pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0]])
    def test_malformed_position_returns_empty(self, bad_pos):
        player = Player().build(farmer=(5, 5))
        assert get_valid_feed_actions_for(player, bad_pos) == []

    def test_out_of_bounds_returns_empty(self):
        player = Player().build(rows=5, cols=5, farmer=(4, 4))
        assert get_valid_feed_actions_for(player, [5, 0]) == []

    def test_empty_tile_returns_empty(self):
        player = Player().build(farmer=(5, 5), shed={"WHEAT": 1})
        assert get_valid_feed_actions_for(player, [5, 5]) == []

    def test_empty_structure_returns_empty(self):
        tiles = [[None] * 10 for _ in range(10)]
        tiles[5][5] = AnimalState(kind="COOP", animal=None)
        player = Player().build(farmer=(5, 5), tiles=tiles, shed={"WHEAT": 1})
        assert get_valid_feed_actions_for(player, [5, 5]) == []

    def test_occupied_coop_no_wheat_returns_empty(self):
        tiles = [[None] * 10 for _ in range(10)]
        tiles[5][5] = _structure(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(5, 5), tiles=tiles, shed={"WHEAT": 0})
        assert get_valid_feed_actions_for(player, [5, 5]) == []

    def test_occupied_coop_with_wheat_returns_feed(self):
        tiles = [[None] * 10 for _ in range(10)]
        tiles[5][5] = _structure(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(5, 5), tiles=tiles, shed={"WHEAT": 1})
        actions = get_valid_feed_actions_for(player, [5, 5])
        assert len(actions) == 1
        assert isinstance(actions[0], FeedActionState)
        assert actions[0].type == "FEED"

    def test_already_fed_returns_empty(self):
        tiles = [[None] * 10 for _ in range(10)]
        tiles[5][5] = _structure(kind="COOP", animal="GOOSE", fed_today=True)
        player = Player().build(farmer=(5, 5), tiles=tiles, shed={"WHEAT": 1})
        assert get_valid_feed_actions_for(player, [5, 5]) == []

    def test_occupied_pasture_with_wheat_returns_feed(self):
        tiles = [[None] * 10 for _ in range(10)]
        tiles[5][5] = _structure(kind="PASTURE", animal="COW")
        player = Player().build(farmer=(5, 5), tiles=tiles, shed={"WHEAT": 1})
        actions = get_valid_feed_actions_for(player, [5, 5])
        assert len(actions) == 1
        assert isinstance(actions[0], FeedActionState)