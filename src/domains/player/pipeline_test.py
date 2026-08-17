"""Smoke tests for the get_<action>_pipeline functions.

Each pipeline returns a list of concrete ActionState instances representing the
downstream actions that follow the triggering action. These tests verify the
functions are importable, return lists, and produce sensible shapes for a few
representative cases — they don't assert exact counts (those are covered by
the production-helper behavior and the action modules' own tests).
"""
from src.domains.player.player import Player
from src.models.action import (
    BaseAction, BuySeedActionState, BuildCoopActionState, BuildPastureActionState,
    CareActionState, CollectFertilizerActionState, DigActionState,
    FeedActionState, FertilizeActionState, HarvestActionState, HireActionState,
    BuyLandActionState, BuyAnimalActionState, BuyProductActionState, MoveActionState,
    PassActionState, PickupActionState, PlaceActionState, PlantActionState,
    SellActionState, WaterActionState,
)
from src.models.farm import PlantState, AnimalState
from src.models.resource import ResourceState

from src.domains.farm.plant import get_plant_pipeline
from src.domains.farm.water import get_water_pipeline
from src.domains.farm.fertilize import get_fertilize_pipeline
from src.domains.farm.harvest import get_harvest_pipeline
from src.domains.farm.collect_fertilizer import get_collect_fertilizer_pipeline
from src.domains.farm.build_structure import get_build_structure_pipeline
from src.domains.farm.feed import get_feed_pipeline
from src.domains.farm.care import get_care_pipeline
from src.domains.farm.dig import get_dig_pipeline
from src.domains.farm.place import get_place_pipeline
from src.domains.farm.pickup import get_pickup_pipeline
from src.domains.farm.move import get_move_pipeline
from src.domains.market.sell import get_sell_pipeline
from src.domains.market.buy_seed import get_buy_seed_pipeline
from src.domains.market.buy_product import get_buy_product_pipeline
from src.domains.market.buy_animal import get_buy_animal_pipeline
from src.domains.market.hire import get_hire_pipeline
from src.domains.market.buy_land import get_buy_land_pipeline


def _all_pipelines(player):
    """Invoke every pipeline against a representative action for its type."""
    farm = player.farms[0]
    return {
        "plant": get_plant_pipeline(PlantActionState(type="PLANT", crop="WHEAT"), player),
        "water": get_water_pipeline(WaterActionState(type="WATER"), player, unit_pos=farm.farmer),
        "fertilize": get_fertilize_pipeline(
            FertilizeActionState(type="FERTILIZE"), player, unit_pos=farm.farmer,
        ),
        "harvest": get_harvest_pipeline(HarvestActionState(type="HARVEST"), player, unit_pos=farm.farmer),
        "collect_fertilizer": get_collect_fertilizer_pipeline(
            CollectFertilizerActionState(type="COLLECT_FERTILIZER"), player, unit_pos=farm.farmer,
        ),
        "build_coop": get_build_structure_pipeline(BuildCoopActionState(type="BUILD_COOP"), player),
        "build_pasture": get_build_structure_pipeline(BuildPastureActionState(type="BUILD_PASTURE"), player),
        "feed": get_feed_pipeline(FeedActionState(type="FEED"), player, unit_pos=farm.farmer),
        "care": get_care_pipeline(CareActionState(type="CARE"), player, unit_pos=farm.farmer),
        "dig": get_dig_pipeline(DigActionState(type="DIG"), player, unit_pos=farm.farmer),
        "place_animal": get_place_pipeline(PlaceActionState(type="PLACE", item="GOOSE", count=1), player),
        "place_product": get_place_pipeline(PlaceActionState(type="PLACE", item="WHEAT", count=3), player),
        "pickup": get_pickup_pipeline(PickupActionState(type="PICKUP", item="WHEAT", count=1), player),
        "move": get_move_pipeline(MoveActionState(type="NORTH"), player, unit_pos=farm.farmer),
        "sell": get_sell_pipeline(SellActionState(type="SELL", item="WHEAT", count=1), player),
        "buy_seed": get_buy_seed_pipeline(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1), player),
        "buy_product": get_buy_product_pipeline(BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=1), player),
        "buy_animal": get_buy_animal_pipeline(BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1), player),
        "hire": get_hire_pipeline(HireActionState(type="HIRE"), player),
        "buy_land": get_buy_land_pipeline(BuyLandActionState(type="BUY_LAND"), player),
    }


class TestPipelinesReturnActionStateLists:
    """Every pipeline returns a list of ActionState instances."""

    def test_all_pipelines_return_lists(self):
        player = Player().build(money=3000.0, seeds={"WHEAT": 5})
        for name, pipeline in _all_pipelines(player).items():
            assert isinstance(pipeline, list), f"{name} did not return a list"
            for a in pipeline:
                assert isinstance(a, BaseAction), (
                    f"{name} returned a non-ActionState: {a!r}"
                )

    def test_empty_pipelines_for_terminal_or_positional(self):
        """SELL is terminal; DIG / PICKUP / MOVE / BUY_PRODUCT / HIRE / BUY_LAND
        have no deterministic next action."""
        player = Player().build(money=3000.0, seeds={"WHEAT": 5})
        farm = player.farms[0]
        assert get_sell_pipeline(SellActionState(type="SELL", item="WHEAT", count=1), player) == []
        assert get_dig_pipeline(DigActionState(type="DIG"), player, unit_pos=farm.farmer) == []
        assert get_pickup_pipeline(PickupActionState(type="PICKUP", item="WHEAT", count=1), player) == []
        assert get_move_pipeline(MoveActionState(type="NORTH"), player, unit_pos=farm.farmer) == []
        assert get_buy_product_pipeline(BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=1), player) == []
        assert get_hire_pipeline(HireActionState(type="HIRE"), player) == []
        assert get_buy_land_pipeline(BuyLandActionState(type="BUY_LAND"), player) == []


class TestPlantPipeline:
    """PLANT WHEAT (one-time, window days 2-4) at day 0 → 3 WATERs + HARVEST + SELL(3)."""

    def test_wheat_pipeline_shape(self):
        player = Player().build(money=3000.0, seeds={"WHEAT": 5})
        pipeline = get_plant_pipeline(PlantActionState(type="PLANT", crop="WHEAT"), player)
        types = [a.type for a in pipeline]
        assert types == ["WATER", "WATER", "WATER", "HARVEST", "SELL"]
        sell = pipeline[-1]
        assert sell.item == "WHEAT"
        assert sell.count == 3  # 3 window waters → 3 yield, capped by max_yield=6

    def test_ongoing_crop_has_no_terminal_sell(self):
        """TOMATO is ongoing → only the WATERs, no HARVEST/SELL (it repeats)."""
        player = Player().build(money=3000.0, seeds={"TOMATO": 5})
        pipeline = get_plant_pipeline(PlantActionState(type="PLANT", crop="TOMATO"), player)
        assert all(a.type == "WATER" for a in pipeline)


class TestBuySeedPipeline:
    """BUY_SEED → PLANT + the plant's downstream chain."""

    def test_buy_seed_wheat(self):
        player = Player().build(money=3000.0)
        pipeline = get_buy_seed_pipeline(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1), player)
        types = [a.type for a in pipeline]
        assert types[0] == "PLANT"
        assert types[1:] == ["WATER", "WATER", "WATER", "HARVEST", "SELL"]


class TestBuildStructurePipeline:
    """BUILD_COOP → PLACE(GOOSE) + the goose per-day care tail."""

    def test_build_coop_starts_with_place_goose(self):
        player = Player().build(money=3000.0)
        pipeline = get_build_structure_pipeline(BuildCoopActionState(type="BUILD_COOP"), player)
        assert pipeline[0].type == "PLACE"
        assert pipeline[0].item == "GOOSE"
        # The tail is the goose's per-day care: FEED/CARE/COLLECT_FERTILIZER
        # every remaining day, HARVEST on yield days, then SELL EGG + SELL FERTILIZER.
        tail_types = [a.type for a in pipeline[1:]]
        assert "FEED" in tail_types
        assert "CARE" in tail_types
        assert "COLLECT_FERTILIZER" in tail_types
        assert tail_types[-2] == "SELL"  # SELL EGG
        assert tail_types[-1] == "SELL"  # SELL FERTILIZER

    def test_build_pasture_places_cow_or_sheep(self):
        player = Player().build(money=3000.0)
        pipeline = get_build_structure_pipeline(BuildPastureActionState(type="BUILD_PASTURE"), player)
        assert pipeline[0].type == "PLACE"
        assert pipeline[0].item in ("COW", "SHEEP")


class TestBuyAnimalPipeline:
    """BUY_ANIMAL → PLACE(animal) + the animal's per-day care tail."""

    def test_buy_goose(self):
        player = Player().build(money=3000.0)
        pipeline = get_buy_animal_pipeline(BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1), player)
        assert pipeline[0].type == "PLACE"
        assert pipeline[0].item == "GOOSE"
        assert any(a.type == "FEED" for a in pipeline[1:])


class TestPlacePipeline:
    """PLACE an animal → the animal's care tail; PLACE a product → SELL it."""

    def test_place_animal_branch(self):
        player = Player().build(money=3000.0)
        pipeline = get_place_pipeline(PlaceActionState(type="PLACE", item="GOOSE", count=1), player)
        assert all(isinstance(a, BaseAction) for a in pipeline)
        assert any(a.type == "FEED" for a in pipeline)

    def test_place_product_branch(self):
        player = Player().build(money=3000.0)
        pipeline = get_place_pipeline(PlaceActionState(type="PLACE", item="WHEAT", count=3), player)
        assert len(pipeline) == 1
        assert pipeline[0].type == "SELL"
        assert pipeline[0].item == "WHEAT"
        assert pipeline[0].count == 3


class TestCollectFertilizerPipeline:
    """COLLECT_FERTILIZER → SELL one FERTILIZER."""

    def test_collect_fertilizer_sells_one(self):
        player = Player().build(money=3000.0)
        pipeline = get_collect_fertilizer_pipeline(
            CollectFertilizerActionState(type="COLLECT_FERTILIZER"), player,
        )
        assert len(pipeline) == 1
        assert pipeline[0].type == "SELL"
        assert pipeline[0].item == "FERTILIZER"
        assert pipeline[0].count == 1


class TestWaterFertilizeFeedCareHarvestOnEmptyTile:
    """Tile-targeting pipelines on a non-matching tile return []."""

    def test_water_on_empty_tile(self):
        player = Player().build(money=3000.0)
        farm = player.farms[0]
        pipeline = get_water_pipeline(WaterActionState(type="WATER"), player, unit_pos=farm.farmer)
        assert pipeline == []

    def test_fertilize_on_empty_tile(self):
        player = Player().build(money=3000.0)
        farm = player.farms[0]
        pipeline = get_fertilize_pipeline(FertilizeActionState(type="FERTILIZE"), player, unit_pos=farm.farmer)
        assert pipeline == []

    def test_harvest_on_empty_tile(self):
        player = Player().build(money=3000.0)
        farm = player.farms[0]
        pipeline = get_harvest_pipeline(HarvestActionState(type="HARVEST"), player, unit_pos=farm.farmer)
        assert pipeline == []

    def test_feed_on_empty_tile(self):
        player = Player().build(money=3000.0)
        farm = player.farms[0]
        pipeline = get_feed_pipeline(FeedActionState(type="FEED"), player, unit_pos=farm.farmer)
        assert pipeline == []

    def test_care_on_empty_tile(self):
        player = Player().build(money=3000.0)
        farm = player.farms[0]
        pipeline = get_care_pipeline(CareActionState(type="CARE"), player, unit_pos=farm.farmer)
        assert pipeline == []


class TestWaterPipelineOnPlantedTile:
    """WATER on a plant tile with yield → HARVEST + SELL(crop, yield_units)."""

    def test_water_on_plant_with_yield(self):
        player = Player().build(money=3000.0)
        farm = player.farms[0]
        farm.tiles[5][5] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120)
        farm.tiles[5][5].yield_units = 4
        pipeline = get_water_pipeline(WaterActionState(type="WATER"), player, unit_pos=[5, 5])
        types = [a.type for a in pipeline]
        assert types == ["HARVEST", "SELL"]
        assert pipeline[-1].item == "WHEAT"
        assert pipeline[-1].count == 4


class TestHarvestPipelineOnTiles:
    """HARVEST on a plant/animal tile → SELL the yield."""

    def test_harvest_on_plant(self):
        player = Player().build(money=3000.0)
        farm = player.farms[0]
        farm.tiles[5][5] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120)
        farm.tiles[5][5].yield_units = 5
        pipeline = get_harvest_pipeline(HarvestActionState(type="HARVEST"), player, unit_pos=[5, 5])
        assert len(pipeline) == 1
        assert pipeline[0].type == "SELL"
        assert pipeline[0].item == "WHEAT"
        assert pipeline[0].count == 5

    def test_harvest_on_animal(self):
        player = Player().build(money=3000.0)
        farm = player.farms[0]
        farm.tiles[5][5] = AnimalState(kind="COOP", animal="GOOSE")
        farm.tiles[5][5].yield_units = 3
        pipeline = get_harvest_pipeline(HarvestActionState(type="HARVEST"), player, unit_pos=[5, 5])
        assert len(pipeline) == 1
        assert pipeline[0].type == "SELL"
        assert pipeline[0].item == "EGG"
        assert pipeline[0].count == 3