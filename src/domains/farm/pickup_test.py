import pytest

from tests.fixtures import _make_env, _turn
from src.domains.farm.pickup import pickup
from src.models.action import PickupActionState
from src.models.environment import StepState


# Shed-adjacent tiles on the default 10x10 board: (4,4), (5,4), (4,5), (5,5).
SHED_ADJ = [(4, 4), (5, 4), (4, 5), (5, 5)]


def _inv(env, idx=0):
    """Ensure and return the unit's inventory dict."""
    while len(env.state.privates[0].inventories) <= idx:
        env.state.privates[0].inventories.append({})
    return env.state.privates[0].inventories[idx]


# ---------------------------------------------------------------------------
# Successful pickup — moves items from shed to inventory.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pos", SHED_ADJ)
def test_pickup_moves_items_from_shed_to_inventory(pos):
    env = _make_env(farmer=pos)
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5

    pickup(env.state, farm, list(pos), PickupActionState(type="PICKUP", item="WHEAT", count=3), 0)

    assert env.state.privates[0].shed.WHEAT == 2
    assert _inv(env).get("WHEAT") == 3


def test_pickup_moves_only_available_when_count_exceeds_supply():
    env = _make_env(farmer=(4, 4))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 2

    pickup(env.state, farm, farm.farmer,
           PickupActionState(type="PICKUP", item="WHEAT", count=5), 0)

    assert env.state.privates[0].shed.WHEAT == 0
    assert _inv(env).get("WHEAT") == 2  # only 2 available


def test_pickup_exact_count_drains_shed_to_zero():
    env = _make_env(farmer=(4, 4))
    farm = env.state.farms[0]
    env.state.privates[0].shed.FERTILIZER = 3

    pickup(env.state, farm, farm.farmer,
           PickupActionState(type="PICKUP", item="FERTILIZER", count=3), 0)

    assert env.state.privates[0].shed.FERTILIZER == 0
    assert _inv(env).get("FERTILIZER") == 3


def test_pickup_adds_to_existing_inventory_stock():
    env = _make_env(farmer=(4, 4))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 4
    _inv(env)["WHEAT"] = 2

    pickup(env.state, farm, farm.farmer,
           PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

    assert env.state.privates[0].shed.WHEAT == 3
    assert _inv(env).get("WHEAT") == 3


@pytest.mark.parametrize("item", [
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP",
])
def test_pickup_works_for_every_shed_item(item):
    env = _make_env(farmer=(4, 4))
    farm = env.state.farms[0]
    setattr(env.state.privates[0].shed, item, 2)

    pickup(env.state, farm, farm.farmer,
           PickupActionState(type="PICKUP", item=item, count=1), 0)

    assert getattr(env.state.privates[0].shed, item) == 1
    assert _inv(env).get(item) == 1


# ---------------------------------------------------------------------------
# No-op conditions.
# ---------------------------------------------------------------------------

def test_pickup_noop_when_not_shed_adjacent():
    env = _make_env(farmer=(0, 0))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5

    pickup(env.state, farm, farm.farmer,
           PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

    assert env.state.privates[0].shed.WHEAT == 5  # unchanged
    assert _inv(env).get("WHEAT") is None


def test_pickup_noop_when_shed_has_none_of_item():
    env = _make_env(farmer=(4, 4))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 0

    pickup(env.state, farm, farm.farmer,
           PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

    assert env.state.privates[0].shed.WHEAT == 0
    assert _inv(env).get("WHEAT") is None


def test_pickup_noop_on_invalid_item():
    env = _make_env(farmer=(4, 4))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5

    pickup(env.state, farm, farm.farmer,
           PickupActionState(type="PICKUP", item="BANANA", count=1), 0)

    assert env.state.privates[0].shed.WHEAT == 5  # untouched
    assert _inv(env).get("BANANA") is None


def test_pickup_does_not_touch_other_shed_items():
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
def test_pickup_noop_on_malformed_or_negative_position(bad_pos):
    env = _make_env(farmer=(4, 4))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5
    pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos

    pickup(env.state, farm, pos,
           PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

    assert env.state.privates[0].shed.WHEAT == 5


def test_pickup_noop_out_of_bounds():
    env = _make_env(rows=5, cols=5, farmer=(2, 2))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5

    pickup(env.state, farm, [5, 0],
           PickupActionState(type="PICKUP", item="WHEAT", count=1), 0)

    assert env.state.privates[0].shed.WHEAT == 5


# ---------------------------------------------------------------------------
# Inventory index — each unit gets its own inventory.
# ---------------------------------------------------------------------------

def test_pickup_writes_to_the_correct_inventory_index():
    env = _make_env(farmer=(4, 4))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5

    # Pad inventories so index 1 already has content.
    env.state.privates[0].inventories = [{}, {"CARROT": 7}]

    pickup(env.state, farm, farm.farmer,
           PickupActionState(type="PICKUP", item="WHEAT", count=2), 0)

    assert env.state.privates[0].inventories[0].get("WHEAT") == 2
    assert env.state.privates[0].inventories[1].get("CARROT") == 7  # hand's untouched
    assert env.state.privates[0].inventories[1].get("WHEAT") is None


# ---------------------------------------------------------------------------
# Integration: dispatch through Environment.step() reaches pickup.
# ---------------------------------------------------------------------------

def test_step_dispatches_pickup_action():
    env = _make_env(farmer=(4, 4))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5

    step = StepState(
        farmer=PickupActionState(type="PICKUP", item="WHEAT", count=2),
        hands=[],
        market=[],
    )
    env.step(_turn(step))

    assert env.state.privates[0].shed.WHEAT == 3
    assert env.state.privates[0].inventories[0].get("WHEAT") == 2


def test_step_pickup_noop_when_not_shed_adjacent():
    env = _make_env(farmer=(0, 0))
    farm = env.state.farms[0]
    env.state.privates[0].shed.WHEAT = 5

    step = StepState(
        farmer=PickupActionState(type="PICKUP", item="WHEAT", count=2),
        hands=[],
        market=[],
    )
    env.step(_turn(step))

    assert env.state.privates[0].shed.WHEAT == 5  # unchanged