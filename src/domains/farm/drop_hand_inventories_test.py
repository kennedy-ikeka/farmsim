"""Tests for end-of-day hand inventory drop to the shed."""
from tests.fixtures import _make_env
from src.domains.farm.drop_hand_inventories import drop_hand_inventories_to_shed
from src.models.farm import FarmState
from src.models.player import PrivateState, ShedState, SeedsState


SHED_FIELDS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK",
               "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP"]


def _zero_shed():
    return ShedState(**{k: 0 for k in SHED_FIELDS})


def _zero_seeds():
    return SeedsState(**{k: 0 for k in ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]})


def _farm_with_hands(num_hands):
    """Build a FarmState with `num_hands` hired hands at distinct positions."""
    hands = [[5, 4 + i] for i in range(num_hands)]
    return FarmState(
        money=0.0, tiles=[[None] * 10 for _ in range(10)],
        farmer=[5, 5], hands=hands,
        unlocked_quadrants=["NW"], hires_today=num_hands,
    )


def _priv_with_inventories(inventories):
    return PrivateState(shed=_zero_shed(), seeds=_zero_seeds(),
                        inventories=inventories)


# ---------------------------------------------------------------------------
# Basic drop — hand inventory moves to shed.
# ---------------------------------------------------------------------------

def test_drop_hand_inventory_moves_all_items_to_shed():
    farm = _farm_with_hands(1)
    priv = _priv_with_inventories([{}, {"WHEAT": 2}])
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 2
    assert priv.inventories[1] == {"WHEAT": 0}  # drained to zero (key kept)


def test_drop_hand_inventory_multiple_items():
    farm = _farm_with_hands(1)
    priv = _priv_with_inventories([{}, {"WHEAT": 3, "EGG": 2, "MILK": 1}])
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 3
    assert priv.shed.EGG == 2
    assert priv.shed.MILK == 1


def test_drop_multiple_hands_each_drops_to_shed():
    farm = _farm_with_hands(2)
    priv = _priv_with_inventories([{}, {"WHEAT": 2}, {"CARROT": 4}])
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 2
    assert priv.shed.CARROT == 4


# ---------------------------------------------------------------------------
# Farmer inventory (index 0) is never touched.
# ---------------------------------------------------------------------------

def test_drop_does_not_touch_farmer_inventory():
    farm = _farm_with_hands(1)
    priv = _priv_with_inventories([{"WHEAT": 5}, {"WHEAT": 2}])
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.inventories[0] == {"WHEAT": 5}  # farmer keeps their inventory
    assert priv.shed.WHEAT == 2  # only the hand's wheat dropped


# ---------------------------------------------------------------------------
# Shed capacity cap — overflow is discarded.
# ---------------------------------------------------------------------------

def test_drop_respects_shed_capacity():
    farm = _farm_with_hands(1)
    # Pre-fill shed with 98 units; hand has 5 wheat → only 2 fit.
    priv = _priv_with_inventories([{}, {"WHEAT": 5}])
    priv.shed.CARROT = 98  # 100 capacity - 98 = 2 space
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 2  # only 2 fit
    assert priv.inventories[1]["WHEAT"] == 3  # 3 left over


def test_drop_no_space_leaves_hand_inventory_untouched():
    farm = _farm_with_hands(1)
    priv = _priv_with_inventories([{}, {"WHEAT": 3}])
    priv.shed.CARROT = 100  # at capacity
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 0
    assert priv.inventories[1] == {"WHEAT": 3}  # nothing moved


# ---------------------------------------------------------------------------
# Empty / zero-count inventories are skipped.
# ---------------------------------------------------------------------------

def test_drop_empty_hand_inventory_is_noop():
    farm = _farm_with_hands(1)
    priv = _priv_with_inventories([{}, {}])
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 0
    assert priv.inventories[1] == {}


def test_drop_skips_zero_count_items():
    farm = _farm_with_hands(1)
    priv = _priv_with_inventories([{}, {"WHEAT": 0, "EGG": 2}])
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 0
    assert priv.shed.EGG == 2


# ---------------------------------------------------------------------------
# Invalid shed items are skipped (not crashed on).
# ---------------------------------------------------------------------------

def test_drop_skips_items_not_in_shed():
    farm = _farm_with_hands(1)
    priv = _priv_with_inventories([{}, {"UNKNOWN_ITEM": 2, "WHEAT": 1}])
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 1  # valid item moved
    # unknown item still in inventory (not a shed field, skipped)
    assert priv.inventories[1].get("UNKNOWN_ITEM") == 2


# ---------------------------------------------------------------------------
# Inventories list shorter than hands — loop bounds safely.
# ---------------------------------------------------------------------------

def test_drop_handles_inventories_shorter_than_hands():
    """If inventories has fewer entries than hands+1, the extra hands are skipped."""
    farm = _farm_with_hands(3)
    # Only inventories[0] and [1] exist; hands 2 and 3 have no inventory slot.
    priv = _priv_with_inventories([{}, {"WHEAT": 2}])
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 2  # hand 1 dropped; hands 2,3 had no slot


# ---------------------------------------------------------------------------
# No hands — nothing happens.
# ---------------------------------------------------------------------------

def test_drop_no_hands_is_noop():
    farm = _farm_with_hands(0)
    priv = _priv_with_inventories([{"WHEAT": 5}])
    drop_hand_inventories_to_shed(farm, priv, shed_capacity=100)
    assert priv.shed.WHEAT == 0
    assert priv.inventories[0] == {"WHEAT": 5}