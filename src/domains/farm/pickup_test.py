import pytest

from tests.fixtures import _make_env, _play
from src.domains.farm.pickup import pickup
from src.models.action import PickupActionState
from src.models.environment import StepState
from src.models.player import InventoryState


# Shed-adjacent tiles on the default 10x10 board: (4,4), (5,4), (4,5), (5,5).
SHED_ADJ = [(4, 4), (5, 4), (4, 5), (5, 5)]


def _inv(env, idx=0):
    """Ensure and return the unit's inventory (an InventoryState)."""
    while len(env.state.privates[0].inventories) <= idx:
        env.state.privates[0].inventories.append(InventoryState())
    return env.state.privates[0].inventories[idx]


class TestPickup:
    """Tests for `pickup`."""

    # ---------------------------------------------------------------------------
    # Successful pickup — moves items from shed to inventory.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("pos", SHED_ADJ)
    def test_moves_items_from_shed_to_inventory(self, pos):
        env = _make_env(farmer=pos)
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 5

        pickup(env.state, farm, list(pos), PickupActionState(type="PICKUP", item="WHEAT", count=3), 0)

        assert env.state.privates[0].shed.WHEAT == 2
        assert _inv(env).WHEAT == 3

    def test_moves_only_available_when_count_exceeds_supply(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 2

        pickup(env.state, farm, farm.farmer,
               PickupActionState(type="PICKUP", item="WHEAT", count=5), 0)

        assert env.state.privates[0].shed.WHEAT == 0
        assert _inv(env).WHEAT == 2  # only 2 available

    def test_exact_count_drains_shed_to_zero(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.FERTILIZER = 3

        pickup(env.state, farm, farm.farmer,
               PickupActionState(type="PICKUP", item="FERTILIZER", count=3), 0)

        assert env.state.privates[0].shed.FERTILIZER == 0
        assert _inv(env).FERTILIZER == 3

    def test_adds_to_existing_inventory_stock(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 4
        _inv(env).WHEAT = 2

        pickup(env.state, farm, farm.farmer,
               PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

        assert env.state.privates[0].shed.WHEAT == 3
        assert _inv(env).WHEAT == 3

    @pytest.mark.parametrize("item", [
        "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
        "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP",
    ])
    def test_works_for_every_shed_item(self, item):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        setattr(env.state.privates[0].shed, item, 2)

        pickup(env.state, farm, farm.farmer,
               PickupActionState(type="PICKUP", item=item, count=1), 0)

        assert getattr(env.state.privates[0].shed, item) == 1
        assert getattr(_inv(env), item) == 1

    # ---------------------------------------------------------------------------
    # No-op conditions.
    # ---------------------------------------------------------------------------

    def test_noop_when_not_shed_adjacent(self):
        env = _make_env(farmer=(0, 0))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 5

        pickup(env.state, farm, farm.farmer,
               PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

        assert env.state.privates[0].shed.WHEAT == 5  # unchanged
        assert _inv(env).WHEAT == 0

    def test_noop_when_shed_has_none_of_item(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 0

        pickup(env.state, farm, farm.farmer,
               PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

        assert env.state.privates[0].shed.WHEAT == 0
        assert _inv(env).WHEAT == 0

    def test_noop_on_invalid_item(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 5

        pickup(env.state, farm, farm.farmer,
               PickupActionState(type="PICKUP", item="BANANA", count=1), 0)

        assert env.state.privates[0].shed.WHEAT == 5  # untouched
        assert getattr(_inv(env), "BANANA", None) is None

    def test_does_not_touch_other_shed_items(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 5
        env.state.privates[0].shed.CARROT = 3

        pickup(env.state, farm, farm.farmer,
               PickupActionState(type="PICKUP", item="WHEAT", count=2), 0)

        assert env.state.privates[0].shed.WHEAT == 3
        assert env.state.privates[0].shed.CARROT == 3  # untouched

    # ---------------------------------------------------------------------------
    # Malformed / out-of-bounds positions are silently skipped.
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize("bad_pos", [None, [4], [], [4, 4, 0], (-1, 4), (4, -1)])
    def test_noop_on_malformed_or_negative_position(self, bad_pos):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 5
        pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos

        pickup(env.state, farm, pos,
               PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

        assert env.state.privates[0].shed.WHEAT == 5

    def test_noop_out_of_bounds(self):
        env = _make_env(rows=5, cols=5, farmer=(2, 2))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 5

        pickup(env.state, farm, [5, 0],
               PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

        assert env.state.privates[0].shed.WHEAT == 5

    # ---------------------------------------------------------------------------
    # Inventory index — each unit gets its own inventory.
    # ---------------------------------------------------------------------------

    def test_writes_to_the_correct_inventory_index(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 5

        # Pad inventories so index 1 already has content.
        env.state.privates[0].inventories = [InventoryState(), InventoryState(CARROT=7)]

        pickup(env.state, farm, farm.farmer,
               PickupActionState(type="PICKUP", item="WHEAT", count=2), 0)

        assert env.state.privates[0].inventories[0].WHEAT == 2
        assert env.state.privates[0].inventories[1].CARROT == 7  # hand's untouched
        assert env.state.privates[0].inventories[1].WHEAT == 0


class TestPickupDispatch:
    """Integration: pickup actions dispatched through `Environment.step` reach `pickup`."""

    def test_dispatches_pickup_action(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 5

        step = StepState(
            farmer=PickupActionState(type="PICKUP", item="WHEAT", count=2),
            hands=[],
            market=[],
        )
        _play(env, step)

        assert env.state.privates[0].shed.WHEAT == 3
        assert env.state.privates[0].inventories[0].WHEAT == 2

    def test_pickup_noop_when_not_shed_adjacent(self):
        env = _make_env(farmer=(0, 0))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 5

        step = StepState(
            farmer=PickupActionState(type="PICKUP", item="WHEAT", count=2),
            hands=[],
            market=[],
        )
        _play(env, step)

        assert env.state.privates[0].shed.WHEAT == 5  # unchanged


# ---------------------------------------------------------------------------
# Tests for `get_valid_pickup_actions_for` (per-unit validity helper).
# ---------------------------------------------------------------------------

from src.domains.farm.pickup import get_valid_pickup_actions_for
from src.domains.player.player import Player


class TestGetValidPickupActionsFor:
    """Tests for `get_valid_pickup_actions_for`."""

    @pytest.mark.parametrize("bad_pos", [None, [5]])
    def test_malformed_unit_pos_returns_empty(self, bad_pos):
        player = Player().build(farmer=(4, 4), shed={"WHEAT": 2})
        assert get_valid_pickup_actions_for(player, bad_pos, 0) == []

    def test_out_of_bounds_returns_empty(self):
        player = Player().build(farmer=(4, 4), shed={"WHEAT": 2})
        assert get_valid_pickup_actions_for(player, [10, 0], 0) == []
        assert get_valid_pickup_actions_for(player, [-1, 0], 0) == []

    def test_shed_adjacent_with_empty_shed_returns_empty(self):
        player = Player().build(farmer=(4, 4))
        assert get_valid_pickup_actions_for(player, [4, 4], 0) == []

    def test_shed_adjacent_with_wheat_returns_one_action(self):
        player = Player().build(farmer=(4, 4), shed={"WHEAT": 2})
        actions = get_valid_pickup_actions_for(player, [4, 4], 0)
        assert len(actions) == 1
        assert actions[0].type == "PICKUP"
        assert actions[0].item == "WHEAT"
        assert actions[0].count == 1

    def test_shed_adjacent_with_multiple_items_returns_one_action_each(self):
        player = Player().build(farmer=(4, 4), shed={"WHEAT": 1, "FERTILIZER": 1})
        actions = get_valid_pickup_actions_for(player, [4, 4], 0)
        items = sorted(a.item for a in actions)
        assert items == ["FERTILIZER", "WHEAT"]
        for a in actions:
            assert a.type == "PICKUP"
            assert a.count == 1

    def test_not_shed_adjacent_returns_empty(self):
        player = Player().build(farmer=(0, 0), shed={"WHEAT": 2})
        assert get_valid_pickup_actions_for(player, [0, 0], 0) == []

    def test_inv_index_does_not_affect_output(self):
        """The helper reads the shed only; `inv_index` is irrelevant to which
        actions are returned (it only selects the destination inventory slot
        for the eventual pickup)."""
        player = Player().build(farmer=(4, 4), shed={"WHEAT": 2},
                              inventories=[InventoryState(), InventoryState(CARROT=1)])
        actions = get_valid_pickup_actions_for(player, [4, 4], 1)
        assert len(actions) == 1
        assert actions[0].item == "WHEAT"