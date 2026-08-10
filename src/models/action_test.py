import pytest
from pydantic import TypeAdapter, ValidationError

from src.models.action import (
    ActionState,
    BuildCoopActionState,
    BuildPastureActionState,
    BuyAnimalActionState,
    BuyLandActionState,
    BuyProductActionState,
    BuySeedActionState,
    CareActionState,
    CollectFertilizerActionState,
    DigActionState,
    FeedActionState,
    FertilizeActionState,
    HarvestActionState,
    HireActionState,
    MoveActionState,
    PickupActionState,
    PlaceActionState,
    PlantActionState,
    SellActionState,
    WaterActionState,
)

adapter = TypeAdapter(ActionState)


def parse(payload):
    return adapter.validate_python(payload)


# ---------------------------------------------------------------------------
# Discriminator dispatch — each `type` tag maps to the right subclass.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"type": "NORTH"}, MoveActionState),
        ({"type": "SOUTH"}, MoveActionState),
        ({"type": "EAST"}, MoveActionState),
        ({"type": "WEST"}, MoveActionState),
        ({"type": "WATER"}, WaterActionState),
        ({"type": "HARVEST"}, HarvestActionState),
        ({"type": "FERTILIZE"}, FertilizeActionState),
        ({"type": "DIG"}, DigActionState),
        ({"type": "HIRE"}, HireActionState),
        ({"type": "BUY_LAND"}, BuyLandActionState),
        ({"type": "PLANT", "crop": "WHEAT"}, PlantActionState),
        ({"type": "BUY_SEED", "crop": "CARROT", "count": 3}, BuySeedActionState),
        ({"type": "BUY_PRODUCT", "item": "FERTILIZER", "count": 2}, BuyProductActionState),
        ({"type": "BUY_ANIMAL", "animal": "COW", "count": 1}, BuyAnimalActionState),
        ({"type": "SELL", "item": "MILK", "count": 4}, SellActionState),
        ({"type": "PICKUP", "item": "WHEAT", "count": 1}, PickupActionState),
        ({"type": "PLACE", "item": "GOOSE", "count": 2}, PlaceActionState),
        ({"type": "BUILD_COOP"}, BuildCoopActionState),
        ({"type": "BUILD_PASTURE"}, BuildPastureActionState),
        ({"type": "FEED"}, FeedActionState),
        ({"type": "COLLECT_FERTILIZER"}, CollectFertilizerActionState),
        ({"type": "CARE"}, CareActionState),
    ],
)
def test_discriminator_dispatch(payload, expected):
    model = parse(payload)
    assert isinstance(model, expected)
    assert model.type == payload["type"]

    
# ---------------------------------------------------------------------------
# Argument-bearing actions — required fields are required, literals enforced.
# ---------------------------------------------------------------------------
def test_plant_requires_crop():
    with pytest.raises(ValidationError):
        parse({"type": "PLANT"})


@pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
def test_plant_accepts_all_crops(crop):
    model = parse({"type": "PLANT", "crop": crop})
    assert isinstance(model, PlantActionState)
    assert model.crop == crop


def test_plant_rejects_unknown_crop():
    with pytest.raises(ValidationError):
        parse({"type": "PLANT", "crop": "BANANA"})


def test_buy_seed_requires_count_and_crop():
    with pytest.raises(ValidationError):
        parse({"type": "BUY_SEED", "crop": "WHEAT"})
    with pytest.raises(ValidationError):
        parse({"type": "BUY_SEED", "crop": "WHEAT", "count": 0})
    with pytest.raises(ValidationError):
        parse({"type": "BUY_SEED", "crop": "BANANA", "count": 1})


def test_buy_product_only_allows_wheat_and_fertilizer():
    for item in ["WHEAT", "FERTILIZER"]:
        model = parse({"type": "BUY_PRODUCT", "item": item, "count": 1})
        assert isinstance(model, BuyProductActionState)
        assert model.item == item

    # Everything else (including other valid sale products) is rejected.
    for item in ["CARROT", "MELON", "EGG", "MILK", "WOOL", "STRAWBERRY", "TOMATO"]:
        with pytest.raises(ValidationError):
            parse({"type": "BUY_PRODUCT", "item": item, "count": 1})


def test_buy_animal_enforces_animal_literal():
    for animal in ["GOOSE", "COW", "SHEEP"]:
        model = parse({"type": "BUY_ANIMAL", "animal": animal, "count": 2})
        assert isinstance(model, BuyAnimalActionState)
        assert model.animal == animal
    with pytest.raises(ValidationError):
        parse({"type": "BUY_ANIMAL", "animal": "PIG", "count": 1})


@pytest.mark.parametrize(
    "item",
    ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"],
)
def test_sell_accepts_every_product(item):
    model = parse({"type": "SELL", "item": item, "count": 1})
    assert isinstance(model, SellActionState)
    assert model.item == item


def test_sell_rejects_non_product():
    with pytest.raises(ValidationError):
        parse({"type": "SELL", "item": "GOOSE", "count": 1})


# ---------------------------------------------------------------------------
# Count constraints — gt=0 on every action that carries a count.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        {"type": "BUY_SEED", "crop": "WHEAT", "count": 0},
        {"type": "BUY_PRODUCT", "item": "WHEAT", "count": -1},
        {"type": "BUY_ANIMAL", "animal": "COW", "count": 0},
        {"type": "SELL", "item": "MILK", "count": 0},
        {"type": "PICKUP", "item": "WHEAT", "count": 0},
        {"type": "PLACE", "item": "GOOSE", "count": -3},
    ],
)
def test_count_must_be_positive(payload):
    with pytest.raises(ValidationError):
        parse(payload)


# ---------------------------------------------------------------------------
# Unknown discriminator tags must be rejected at the union level.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        {"type": "FLY"},
        {"type": "BUY"},
        {"type": "SELL_CROP", "item": "WHEAT", "count": 1},
        {"type": "water"},  # case-sensitive
        {},
    ],
)
def test_unknown_type_rejected(payload):
    with pytest.raises(ValidationError):
        parse(payload)


# ---------------------------------------------------------------------------
# No-arg actions ignore extra fields only if not provided; they still
# discriminate correctly and reject nothing on their own schema.
# ---------------------------------------------------------------------------

def test_no_arg_actions_carry_only_type():
    for payload, cls in [
        ({"type": "WATER"}, WaterActionState),
        ({"type": "HARVEST"}, HarvestActionState),
        ({"type": "FERTILIZE"}, FertilizeActionState),
        ({"type": "DIG"}, DigActionState),
        ({"type": "HIRE"}, HireActionState),
        ({"type": "BUY_LAND"}, BuyLandActionState),
    ]:
        model = parse(payload)
        assert isinstance(model, cls)
        # No extra fields defined on these models.
        assert set(type(model).model_fields) == {"type"}


# ---------------------------------------------------------------------------
# Round-trip: a model built directly should dump back to the same payload.
# ---------------------------------------------------------------------------

def test_round_trip_buy_seed():
    model = BuySeedActionState(type="BUY_SEED", crop="MELON", count=5)
    dumped = model.model_dump()
    assert dumped == {"type": "BUY_SEED", "crop": "MELON", "count": 5}
    # And the dumped dict re-validates through the union.
    assert isinstance(parse(dumped), BuySeedActionState)


def test_round_trip_sell():
    model = SellActionState(type="SELL", item="WOOL", count=12)
    dumped = model.model_dump()
    assert dumped == {"type": "SELL", "item": "WOOL", "count": 12}
    assert isinstance(parse(dumped), SellActionState)