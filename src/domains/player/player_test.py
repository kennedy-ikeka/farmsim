from src.domains.player.player import (
    Player,
    get_valid_farm_actions_for,
    get_valid_market_actions,
)
from src.models.action import (
    BuyAnimalActionState,
    BuyLandActionState,
    BuyProductActionState,
    BuySeedActionState,
    BuildCoopActionState,
    BuildPastureActionState,
    CareActionState,
    CollectFertilizerActionState,
    DigActionState,
    FeedActionState,
    FertilizeActionState,
    HarvestActionState,
    HireActionState,
    MoveActionState,
    PassActionState,
    PickupActionState,
    PlaceActionState,
    PlantActionState,
    SellActionState,
    WaterActionState,
)
from src.models.farm import AnimalState, PlantState, WeedState
from src.models.player import InventoryState
from src.models.environment import ValidStepsState


def _all_actions(vsa: ValidStepsState) -> list:
    """Flatten a ValidStepsState into a flat list of all actions."""
    actions = list(vsa.farmer)
    for hand in vsa.hands:
        actions.extend(hand)
    actions.extend(vsa.market)
    return actions


def _move_types(actions):
    return sorted(a.type for a in actions if isinstance(a, MoveActionState))


def _types(actions):
    return sorted(a.type for a in actions)


class TestGetValidActions:
    """Tests for `Player.get_valid_actions` — aggregation across units + actions."""

    def test_includes_pass(self):
        player = Player().build(farmer=(5, 5))
        assert "PASS" in _types(_all_actions(player.get_valid_actions()))

    def test_move_set_center_farmer_no_hands(self):
        """The four in-bounds farmer moves are present (other action types may
        also appear when the tile is empty, so filter to moves here)."""
        player = Player().build(farmer=(5, 5), hands=[])
        assert _move_types(_all_actions(player.get_valid_actions())) == ["EAST", "NORTH", "SOUTH", "WEST"]

    def test_move_set_corner_farmer(self):
        player = Player().build(farmer=(0, 0), hands=[])
        assert _move_types(_all_actions(player.get_valid_actions())) == ["EAST", "SOUTH"]

    def test_move_union_across_hands(self):
        """One hand at NW corner, one at SE — the move union is still all four."""
        player = Player().build(farmer=(5, 5), hands=[[0, 0], [9, 9]])
        assert set(_move_types(_all_actions(player.get_valid_actions()))) == {"EAST", "NORTH", "SOUTH", "WEST"}

    def test_move_count_reflects_every_unit(self):
        """4 (farmer) + 2 (hand 0) + 2 (hand 1) = 8 move actions, plus 1 pass."""
        player = Player().build(farmer=(5, 5), hands=[[0, 0], [9, 9]])
        actions = _all_actions(player.get_valid_actions())
        assert sum(1 for a in actions if isinstance(a, MoveActionState)) == 8
        assert sum(1 for a in actions if isinstance(a, PassActionState)) == 1

    def test_move_union_edge_farmer_with_edge_hand(self):
        player = Player().build(farmer=(0, 5), hands=[[9, 0]])
        types = _move_types(_all_actions(player.get_valid_actions()))
        assert set(types) == {"EAST", "NORTH", "SOUTH", "WEST"}

    def test_includes_build_on_empty_tile(self):
        """A farmer on an empty tile gets BUILD_COOP and BUILD_PASTURE."""
        player = Player().build(farmer=(5, 5), hands=[])
        types = _types(_all_actions(player.get_valid_actions()))
        assert "BUILD_COOP" in types
        assert "BUILD_PASTURE" in types

    def test_includes_plant_with_seeds_on_empty_tile(self):
        """A farmer on an empty tile with WHEAT seeds gets a PLANT action."""
        player = Player().build(farmer=(5, 5), seeds={"WHEAT": 2})
        plants = [a for a in _all_actions(player.get_valid_actions()) if isinstance(a, PlantActionState)]
        assert len(plants) == 1
        assert plants[0].crop == "WHEAT"

    def test_includes_water_on_unwatered_plant(self):
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        waters = [a for a in _all_actions(player.get_valid_actions()) if isinstance(a, WaterActionState)]
        assert len(waters) == 1

    def test_includes_harvest_on_mature_plant(self):
        """A mature plant with yield_units > 0 yields a HARVEST action."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100,
                           yield_units=3)
        player = Player().build(farmer=(0, 0), tiles=[[plant]], day=2)
        harvests = [a for a in _all_actions(player.get_valid_actions()) if isinstance(a, HarvestActionState)]
        assert len(harvests) == 1

    def test_includes_dig_on_weed(self):
        player = Player().build(farmer=(0, 0), tiles=[[WeedState()]])
        assert any(isinstance(a, DigActionState) for a in _all_actions(player.get_valid_actions()))

    def test_includes_fertilize_on_plant_with_fertilizer(self):
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]], shed={"FERTILIZER": 1})
        assert any(isinstance(a, FertilizeActionState) for a in _all_actions(player.get_valid_actions()))

    def test_includes_pickup_when_shed_adjacent_with_stock(self):
        # (4,4) is one of the four shed-adjacent tiles on a 10x10 grid.
        player = Player().build(farmer=(4, 4), shed={"WHEAT": 1})
        pickups = [a for a in _all_actions(player.get_valid_actions()) if isinstance(a, PickupActionState)]
        assert len(pickups) == 1
        assert pickups[0].item == "WHEAT"

    def test_no_pickup_when_not_shed_adjacent(self):
        player = Player().build(farmer=(0, 0), shed={"WHEAT": 1})
        assert not any(isinstance(a, PickupActionState) for a in _all_actions(player.get_valid_actions()))

    def test_includes_feed_on_hungry_animal_with_wheat(self):
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]], shed={"WHEAT": 1})
        assert any(isinstance(a, FeedActionState) for a in _all_actions(player.get_valid_actions()))

    def test_includes_collect_fertilizer_when_available(self):
        coop = AnimalState(kind="COOP", animal="GOOSE", fertilizer_available=1)
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        assert any(isinstance(a, CollectFertilizerActionState)
                   for a in _all_actions(player.get_valid_actions()))

    def test_includes_care_on_uncared_animal(self):
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        assert any(isinstance(a, CareActionState) for a in _all_actions(player.get_valid_actions()))

    def test_includes_place_animal_on_matching_empty_structure(self):
        coop = AnimalState(kind="COOP", animal=None)
        player = Player().build(farmer=(0, 0), tiles=[[coop]],
                              inventories=[InventoryState(GOOSE=1)])
        places = [a for a in _all_actions(player.get_valid_actions()) if isinstance(a, PlaceActionState)]
        assert any(p.item == "GOOSE" for p in places)

    def test_hand_actions_aggregated(self):
        """A hand on an empty tile also gets BUILD actions (inv_index 1)."""
        player = Player().build(farmer=(5, 5), hands=[[4, 4]])
        # Farmer + hand each on empty tiles -> 2 BUILD_COOP + 2 BUILD_PASTURE.
        builds = [a for a in _all_actions(player.get_valid_actions())
                  if isinstance(a, (BuildCoopActionState, BuildPastureActionState))]
        assert len(builds) == 4


class TestGetValidFarmActionsFor:
    """Tests for the `get_valid_farm_actions_for` aggregator (per-unit)."""

    def test_empty_tile_yields_moves_and_builds(self):
        """A unit on an empty in-bounds tile gets moves + both BUILD actions."""
        player = Player().build(farmer=(5, 5))
        actions = get_valid_farm_actions_for(player, [5, 5], 0)
        types = _types(actions)
        assert "BUILD_COOP" in types
        assert "BUILD_PASTURE" in types
        assert "NORTH" in types and "SOUTH" in types

    def test_malformed_position_returns_empty(self):
        player = Player().build(farmer=(5, 5))
        assert get_valid_farm_actions_for(player, None, 0) == []
        assert get_valid_farm_actions_for(player, [5], 0) == []

    def test_out_of_bounds_returns_empty(self):
        player = Player().build(farmer=(5, 5))
        assert get_valid_farm_actions_for(player, [-5, -5], 0) == []
        assert get_valid_farm_actions_for(player, [100, 100], 0) == []

    def test_locked_tile_blocks_build_and_plant(self):
        """A LOCKED tile is not None, so BUILD/PLANT no-op; moves still valid."""
        player = Player().build(farmer=(0, 0), tiles=[["LOCKED"]], rows=1, cols=1,
                              seeds={"WHEAT": 1})
        actions = get_valid_farm_actions_for(player, [0, 0], 0)
        types = _types(actions)
        assert "BUILD_COOP" not in types
        assert "PLANT" not in types


class TestGetValidMarketActions:
    """Tests for `get_valid_market_actions` / `Player.get_valid_market_actions`."""

    def test_empty_when_no_money_and_no_stock(self):
        """Default state (money=0, empty shed, empty market) yields no market actions."""
        player = Player().build()
        assert player.get_valid_market_actions() == []
        assert get_valid_market_actions(player) == []

    def test_buy_seed_when_affordable(self):
        """With money >= cheapest seed (WHEAT=10), BUY_SEED appears."""
        player = Player().build(money=10)
        seeds = [a for a in player.get_valid_market_actions()
                 if isinstance(a, BuySeedActionState)]
        assert len(seeds) == 1
        assert seeds[0].crop == "WHEAT"

    def test_buy_seed_all_crops_when_rich(self):
        """money=3000 affords every seed (max cost 100)."""
        player = Player().build(money=3000)
        crops = sorted(a.crop for a in player.get_valid_market_actions()
                       if isinstance(a, BuySeedActionState))
        assert crops == ["CARROT", "MELON", "STRAWBERRY", "TOMATO", "WHEAT"]

    def test_buy_product_when_in_stock_and_affordable(self):
        player = Player().build(money=3000,
                              market_inventory={"WHEAT": 100, "FERTILIZER": 50},
                              market_prices={"WHEAT": 25, "FERTILIZER": 100})
        items = sorted(a.item for a in player.get_valid_market_actions()
                       if isinstance(a, BuyProductActionState))
        assert items == ["FERTILIZER", "WHEAT"]

    def test_buy_product_filters_by_affordability(self):
        """money=50 affords WHEAT(25) but not FERTILIZER(100)."""
        player = Player().build(money=50,
                              market_inventory={"WHEAT": 100, "FERTILIZER": 50},
                              market_prices={"WHEAT": 25, "FERTILIZER": 100})
        items = [a.item for a in player.get_valid_market_actions()
                 if isinstance(a, BuyProductActionState)]
        assert items == ["WHEAT"]

    def test_buy_animal_when_affordable(self):
        """GOOSE=300, COW=400, SHEEP=500. money=300 → only GOOSE."""
        player = Player().build(money=300)
        animals = sorted(a.animal for a in player.get_valid_market_actions()
                         if isinstance(a, BuyAnimalActionState))
        assert animals == ["GOOSE"]

    def test_sell_when_shed_has_stock_and_price_positive(self):
        """shed.WHEAT=5 + price.WHEAT=25 → a SELL action; price=0 → none."""
        player = Player().build(money=3000, shed={"WHEAT": 5},
                              market_prices={"WHEAT": 25})
        sells = [a for a in player.get_valid_market_actions()
                 if isinstance(a, SellActionState)]
        assert len(sells) == 1
        assert sells[0].item == "WHEAT"

    def test_sell_no_op_when_price_zero(self):
        player = Player().build(money=3000, shed={"WHEAT": 5},
                              market_prices={"WHEAT": 0})
        assert not any(isinstance(a, SellActionState)
                       for a in player.get_valid_market_actions())

    def test_hire_when_affordable(self):
        """hires_today=0 → cost=1; money=1 affords it."""
        player = Player().build(money=1, hires_today=0)
        assert any(isinstance(a, HireActionState)
                   for a in player.get_valid_market_actions())

    def test_hire_no_op_when_broke(self):
        """hires_today=2 → cost=2; money=1 can't afford."""
        player = Player().build(money=1, hires_today=2)
        assert not any(isinstance(a, HireActionState)
                       for a in player.get_valid_market_actions())

    def test_buy_land_when_affordable(self):
        """NW unlocked (default), NE next at 1000; money=1000 affords it."""
        player = Player().build(money=1000, unlocked_quadrants=["NW"])
        assert any(isinstance(a, BuyLandActionState)
                   for a in player.get_valid_market_actions())

    def test_buy_land_no_op_when_all_unlocked(self):
        player = Player().build(money=10000,
                              unlocked_quadrants=["NW", "NE", "SW", "SE"])
        assert not any(isinstance(a, BuyLandActionState)
                       for a in player.get_valid_market_actions())

    def test_aggregates_all_six_types(self):
        """A rich player with stock and shed items gets all six action types."""
        player = Player().build(
            money=5000,
            shed={"WHEAT": 5},
            market_inventory={"WHEAT": 100, "FERTILIZER": 50},
            market_prices={"WHEAT": 25, "FERTILIZER": 100},
            hires_today=0,
            unlocked_quadrants=["NW"],
        )
        types = set(a.type for a in player.get_valid_market_actions())
        assert {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL", "HIRE", "BUY_LAND"} <= types