import pytest

from tests.fixtures import _make_env, _play
from src.domains.farm.place import place
from src.models.action import PlaceActionState
from src.models.environment import StepState
from src.models.farm import AnimalState, PlantState, WeedState
from src.models.player import InventoryState


SHED_ADJ = [(4, 4), (5, 4), (4, 5), (5, 5)]


def _inv(env, idx=0):
    while len(env.state.privates[0].inventories) <= idx:
        env.state.privates[0].inventories.append(InventoryState())
    return env.state.privates[0].inventories[idx]


def _empty_structure(kind="COOP"):
    return AnimalState(kind=kind, animal=None)


class TestPlace:
    """Tests for `place`."""

    # ===========================================================================
    # Animal placement — standing on a matching unoccupied structure.
    # ===========================================================================

    @pytest.mark.parametrize("animal, kind", [
        ("GOOSE", "COOP"),
        ("COW", "PASTURE"),
        ("SHEEP", "PASTURE"),
    ])
    def test_animal_on_matching_empty_structure(self, animal, kind):
        env = _make_env(farmer=(0, 0), day=3)
        farm = env.state.farms[0]
        farm.tiles[0][0] = _empty_structure(kind=kind)
        setattr(_inv(env), animal, 2)

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item=animal, count=1), 0)

        tile = farm.tiles[0][0]
        assert tile.animal == animal
        assert tile.placed_day == 3
        assert tile.fed_today is False
        assert tile.consecutive_unfed == 0  # fresh start
        assert tile.cared_today is False
        assert tile.yield_units == 0
        assert tile.fertilizer_available == 0
        assert tile.pending_care_bonus == 0
        assert getattr(_inv(env), animal) == 1  # one consumed

    def test_animal_resets_fields_on_reused_structure(self):
        """Placing on a structure that previously held an escaped animal resets
        all animal-related fields to a fresh start."""
        env = _make_env(farmer=(0, 0), day=5)
        farm = env.state.farms[0]
        farm.tiles[0][0] = AnimalState(
            kind="COOP", animal=None, fed_today=True, consecutive_unfed=2,
            cared_today=True, yield_units=3, fertilizer_available=1,
            pending_care_bonus=4, placed_day=1,
        )
        _inv(env).GOOSE = 1

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="GOOSE", count=1), 0)

        tile = farm.tiles[0][0]
        assert tile.animal == "GOOSE"
        assert tile.placed_day == 5
        assert tile.consecutive_unfed == 0
        assert tile.yield_units == 0
        assert tile.fertilizer_available == 0
        assert tile.pending_care_bonus == 0

    def test_animal_count_is_ignored(self):
        """The count argument is ignored for animal placement — exactly one is placed."""
        env = _make_env(farmer=(0, 0))
        farm = env.state.farms[0]
        farm.tiles[0][0] = _empty_structure(kind="COOP")
        _inv(env).GOOSE = 3

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="GOOSE", count=10), 0)

        assert farm.tiles[0][0].animal == "GOOSE"
        assert _inv(env).GOOSE == 2  # only one consumed

    def test_animal_removes_inventory_entry_when_depleted(self):
        env = _make_env(farmer=(0, 0))
        farm = env.state.farms[0]
        farm.tiles[0][0] = _empty_structure(kind="COOP")
        _inv(env).GOOSE = 1

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="GOOSE", count=1), 0)

        assert farm.tiles[0][0].animal == "GOOSE"
        assert _inv(env).GOOSE == 0  # field kept at 0 (depleted)

    # ---------------------------------------------------------------------------
    # Animal placement no-ops.
    # ---------------------------------------------------------------------------

    def test_animal_noop_on_wrong_structure_kind(self):
        env = _make_env(farmer=(0, 0))
        farm = env.state.farms[0]
        farm.tiles[0][0] = _empty_structure(kind="PASTURE")  # COW needs pasture, GOOSE needs coop
        _inv(env).GOOSE = 2

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="GOOSE", count=1), 0)

        assert farm.tiles[0][0].animal is None  # not placed
        assert _inv(env).GOOSE == 2  # not consumed

    def test_animal_noop_when_structure_already_occupied(self):
        env = _make_env(farmer=(0, 0))
        farm = env.state.farms[0]
        farm.tiles[0][0] = AnimalState(kind="COOP", animal="GOOSE")
        _inv(env).GOOSE = 2

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="GOOSE", count=1), 0)

        assert farm.tiles[0][0].animal == "GOOSE"  # unchanged (the original)
        assert _inv(env).GOOSE == 2  # not consumed

    def test_animal_noop_when_not_in_inventory(self):
        env = _make_env(farmer=(0, 0))
        farm = env.state.farms[0]
        farm.tiles[0][0] = _empty_structure(kind="COOP")
        # no GOOSE in inventory

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="GOOSE", count=1), 0)

        assert farm.tiles[0][0].animal is None  # not placed

    def test_animal_noop_on_non_structure_tile(self):
        env = _make_env(farmer=(0, 0))
        farm = env.state.farms[0]
        farm.tiles[0][0] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120)
        _inv(env).GOOSE = 2

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="GOOSE", count=1), 0)

        assert isinstance(farm.tiles[0][0], PlantState)  # untouched
        assert _inv(env).GOOSE == 2

    # ===========================================================================
    # Shed drop — standing orthogonally adjacent to the shed.
    # ===========================================================================

    @pytest.mark.parametrize("pos", SHED_ADJ)
    def test_shed_drop_moves_items_to_shed(self, pos):
        env = _make_env(farmer=pos)
        farm = env.state.farms[0]
        _inv(env).WHEAT = 5

        place(env.state, farm, list(pos),
              PlaceActionState(type="PLACE", item="WHEAT", count=3), 0)

        assert env.state.privates[0].shed.WHEAT == 3
        assert _inv(env).WHEAT == 2

    def test_shed_drop_moves_only_available_when_count_exceeds_held(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        _inv(env).WHEAT = 2

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="WHEAT", count=5), 0)

        assert env.state.privates[0].shed.WHEAT == 2
        assert _inv(env).WHEAT == 0

    def test_shed_drop_capped_by_shed_capacity(self):
        """Shed is near full; only the remaining capacity is accepted."""
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 98  # 2 slots left
        _inv(env).WHEAT = 5

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="WHEAT", count=5), 0)

        assert env.state.privates[0].shed.WHEAT == 100  # capped
        assert _inv(env).WHEAT == 3  # excess stays in inventory

    def test_shed_drop_noop_when_shed_full(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 100
        _inv(env).CARROT = 5

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="CARROT", count=3), 0)

        assert env.state.privates[0].shed.CARROT == 0  # nothing accepted
        assert _inv(env).CARROT == 5  # all stays in inventory

    def test_shed_drop_noop_when_not_shed_adjacent(self):
        env = _make_env(farmer=(0, 0))
        farm = env.state.farms[0]
        _inv(env).WHEAT = 5

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="WHEAT", count=3), 0)

        assert env.state.privates[0].shed.WHEAT == 0  # nothing dropped
        assert _inv(env).WHEAT == 5

    def test_shed_drop_noop_on_invalid_item(self):
        """A PLACE action whose `item` is not a valid shed field no-ops —
        the strict InventoryState can never hold BANANA, but a malformed
        action could still request it."""
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        _inv(env).WHEAT = 5

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="BANANA", count=3), 0)

        assert _inv(env).WHEAT == 5  # not moved
        assert env.state.privates[0].shed.WHEAT == 0  # shed untouched

    def test_shed_drop_noop_when_inventory_empty(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="WHEAT", count=3), 0)

        assert env.state.privates[0].shed.WHEAT == 0

    def test_shed_drop_counts_all_fields_toward_capacity(self):
        """Capacity is total items across all shed fields, not per-item."""
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        env.state.privates[0].shed.WHEAT = 50
        env.state.privates[0].shed.CARROT = 48  # 98 total; 2 slots left
        _inv(env).MILK = 5

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="MILK", count=5), 0)

        assert env.state.privates[0].shed.MILK == 2  # only 2 fit
        assert _inv(env).MILK == 3  # excess stays

    # ===========================================================================
    # Animal placement takes priority over shed drop on a matching structure that
    # also happens to be shed-adjacent.
    # ===========================================================================

    def test_animal_priority_over_shed_drop(self):
        """On a matching structure at a shed-adjacent tile, the animal is placed
        rather than dropped into the shed."""
        env = _make_env(farmer=(4, 4))  # shed-adjacent
        farm = env.state.farms[0]
        farm.tiles[4][4] = _empty_structure(kind="COOP")
        _inv(env).GOOSE = 2

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="GOOSE", count=1), 0)

        assert farm.tiles[4][4].animal == "GOOSE"  # placed on coop
        assert env.state.privates[0].shed.GOOSE == 0  # not dropped into shed
        assert _inv(env).GOOSE == 1

    def test_non_matching_animal_falls_through_to_shed_drop(self):
        """On a non-matching structure at a shed-adjacent tile, the animal is
        dropped into the shed."""
        env = _make_env(farmer=(4, 4))  # shed-adjacent
        farm = env.state.farms[0]
        farm.tiles[4][4] = _empty_structure(kind="PASTURE")  # COW needs pasture; GOOSE needs coop
        _inv(env).GOOSE = 2

        place(env.state, farm, farm.farmer,
              PlaceActionState(type="PLACE", item="GOOSE", count=1), 0)

        assert farm.tiles[4][4].animal is None  # not placed (wrong structure)
        assert env.state.privates[0].shed.GOOSE == 1  # dropped into shed
        assert _inv(env).GOOSE == 1

    # ===========================================================================
    # Malformed / out-of-bounds positions are silently skipped.
    # ===========================================================================

    @pytest.mark.parametrize("bad_pos", [None, [4], [], [4, 4, 0], (-1, 4), (4, -1)])
    def test_noop_on_malformed_or_negative_position(self, bad_pos):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        _inv(env).WHEAT = 5
        pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos

        place(env.state, farm, pos,
               PlaceActionState(type="PLACE", item="WHEAT", count=1), 0)

        assert env.state.privates[0].shed.WHEAT == 0
        assert _inv(env).WHEAT == 5

    def test_noop_out_of_bounds(self):
        env = _make_env(rows=5, cols=5, farmer=(2, 2))
        farm = env.state.farms[0]
        _inv(env).WHEAT = 5

        place(env.state, farm, [5, 0],
              PlaceActionState(type="PLACE", item="WHEAT", count=1), 0)

        assert env.state.privates[0].shed.WHEAT == 0
        assert _inv(env).WHEAT == 5


class TestPlaceDispatch:
    """Integration: place actions dispatched through `Environment.step` reach `place`."""

    def test_dispatches_place_animal(self):
        env = _make_env(farmer=(3, 3), day=2)
        farm = env.state.farms[0]
        farm.tiles[3][3] = _empty_structure(kind="COOP")
        _inv(env).GOOSE = 1

        step = StepState(
            farmer=PlaceActionState(type="PLACE", item="GOOSE", count=1),
            hands=[],
            market=[],
        )
        _play(env, step)

        assert env.state.farms[0].tiles[3][3].animal == "GOOSE"
        assert env.state.privates[0].inventories[0].GOOSE == 0

    def test_dispatches_place_shed_drop(self):
        env = _make_env(farmer=(4, 4))
        farm = env.state.farms[0]
        _inv(env).WHEAT = 5

        step = StepState(
            farmer=PlaceActionState(type="PLACE", item="WHEAT", count=3),
            hands=[],
            market=[],
        )
        _play(env, step)

        assert env.state.privates[0].shed.WHEAT == 3
        assert env.state.privates[0].inventories[0].WHEAT == 2


# ---------------------------------------------------------------------------
# Tests for `get_valid_place_actions_for` (per-unit validity helper).
# ---------------------------------------------------------------------------

from src.domains.farm.place import get_valid_place_actions_for
from src.domains.player.player import Player


def _tiles_with(tile, rows=10, cols=10, pos=(0, 0)):
    """Build a rows x cols tile grid with `tile` placed at `pos`."""
    grid = [[None] * cols for _ in range(rows)]
    grid[pos[0]][pos[1]] = tile
    return grid


class TestGetValidPlaceActionsFor:
    """Tests for `get_valid_place_actions_for`."""

    @pytest.mark.parametrize("bad_pos", [None, [5]])
    def test_malformed_unit_pos_returns_empty(self, bad_pos):
        player = Player().build(farmer=(0, 0), inventories=[InventoryState(WHEAT=1)])
        assert get_valid_place_actions_for(player, bad_pos, 0) == []

    def test_out_of_bounds_returns_empty(self):
        player = Player().build(farmer=(0, 0), inventories=[InventoryState(WHEAT=1)])
        assert get_valid_place_actions_for(player, [10, 0], 0) == []
        assert get_valid_place_actions_for(player, [-1, 0], 0) == []

    def test_animal_on_matching_empty_coop_returns_goose(self):
        coop = _empty_structure(kind="COOP")
        player = Player().build(farmer=(0, 0), tiles=_tiles_with(coop),
                              inventories=[InventoryState(GOOSE=1)])
        actions = get_valid_place_actions_for(player, [0, 0], 0)
        assert len(actions) == 1
        assert actions[0].type == "PLACE"
        assert actions[0].item == "GOOSE"
        assert actions[0].count == 1

    def test_animal_on_matching_empty_pasture_returns_cow(self):
        pasture = _empty_structure(kind="PASTURE")
        player = Player().build(farmer=(0, 0), tiles=_tiles_with(pasture),
                              inventories=[InventoryState(COW=1)])
        actions = get_valid_place_actions_for(player, [0, 0], 0)
        assert len(actions) == 1
        assert actions[0].type == "PLACE"
        assert actions[0].item == "COW"
        assert actions[0].count == 1

    def test_animal_noop_when_coop_already_occupied(self):
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=_tiles_with(coop),
                              inventories=[InventoryState(GOOSE=1)])
        assert get_valid_place_actions_for(player, [0, 0], 0) == []

    def test_animal_noop_when_wrong_structure_kind(self):
        """COW needs a PASTURE; a COOP tile does not match, and (0,0) on a
        10x10 grid is not shed-adjacent, so no shed-drop fallback fires."""
        coop = _empty_structure(kind="COOP")
        player = Player().build(farmer=(0, 0), tiles=_tiles_with(coop),
                              inventories=[InventoryState(COW=1)])
        assert get_valid_place_actions_for(player, [0, 0], 0) == []

    def test_shed_drop_when_shed_adjacent_returns_wheat(self):
        player = Player().build(farmer=(4, 4), inventories=[InventoryState(WHEAT=1)])
        actions = get_valid_place_actions_for(player, [4, 4], 0)
        assert len(actions) == 1
        assert actions[0].type == "PLACE"
        assert actions[0].item == "WHEAT"
        assert actions[0].count == 1

    def test_shed_drop_noop_when_not_shed_adjacent(self):
        """(0,0) on a 10x10 grid is not shed-adjacent and has no matching
        structure, so no PLACE action is produced."""
        player = Player().build(farmer=(0, 0), inventories=[InventoryState(WHEAT=1)])
        assert get_valid_place_actions_for(player, [0, 0], 0) == []

    def test_shed_drop_noop_when_shed_full(self):
        player = Player().build(farmer=(4, 4), shed={"WHEAT": 100},
                              inventories=[InventoryState(WHEAT=1)])
        assert get_valid_place_actions_for(player, [4, 4], 0) == []

    def test_empty_inventory_returns_empty(self):
        player = Player().build(farmer=(4, 4))
        assert get_valid_place_actions_for(player, [4, 4], 0) == []

    def test_inv_index_selects_which_inventory(self):
        """With inventories=[InventoryState(), InventoryState(GOOSE=1)] and
        inv_index=1, the helper reads the second inventory slot and returns
        a GOOSE placement."""
        coop = _empty_structure(kind="COOP")
        player = Player().build(farmer=(0, 0), tiles=_tiles_with(coop),
                              inventories=[InventoryState(), InventoryState(GOOSE=1)])
        actions = get_valid_place_actions_for(player, [0, 0], 1)
        assert len(actions) == 1
        assert actions[0].item == "GOOSE"