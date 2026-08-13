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


class TestDiscriminator:
    """Tests for discriminator dispatch — each `type` tag maps to the right subclass."""

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
    def test_dispatch(self, payload, expected):
        model = parse(payload)
        assert isinstance(model, expected)
        assert model.type == payload["type"]


class TestPlant:
    """Tests for `PlantActionState` — crop field required and enforced."""

    def test_requires_crop(self):
        with pytest.raises(ValidationError):
            parse({"type": "PLANT"})

    @pytest.mark.parametrize("crop", ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"])
    def test_accepts_all_crops(self, crop):
        model = parse({"type": "PLANT", "crop": crop})
        assert isinstance(model, PlantActionState)
        assert model.crop == crop

    def test_rejects_unknown_crop(self):
        with pytest.raises(ValidationError):
            parse({"type": "PLANT", "crop": "BANANA"})


class TestBuySeed:
    """Tests for `BuySeedActionState` — required count and crop."""

    def test_requires_count_and_crop(self):
        with pytest.raises(ValidationError):
            parse({"type": "BUY_SEED", "crop": "WHEAT"})
        with pytest.raises(ValidationError):
            parse({"type": "BUY_SEED", "crop": "WHEAT", "count": 0})
        with pytest.raises(ValidationError):
            parse({"type": "BUY_SEED", "crop": "BANANA", "count": 1})


class TestBuyProduct:
    """Tests for `BuyProductActionState` — item literal restricted."""

    def test_only_allows_wheat_and_fertilizer(self):
        for item in ["WHEAT", "FERTILIZER"]:
            model = parse({"type": "BUY_PRODUCT", "item": item, "count": 1})
            assert isinstance(model, BuyProductActionState)
            assert model.item == item

        # Everything else (including other valid sale products) is rejected.
        for item in ["CARROT", "MELON", "EGG", "MILK", "WOOL", "STRAWBERRY", "TOMATO"]:
            with pytest.raises(ValidationError):
                parse({"type": "BUY_PRODUCT", "item": item, "count": 1})


class TestBuyAnimal:
    """Tests for `BuyAnimalActionState` — animal literal enforced."""

    def test_enforces_animal_literal(self):
        for animal in ["GOOSE", "COW", "SHEEP"]:
            model = parse({"type": "BUY_ANIMAL", "animal": animal, "count": 2})
            assert isinstance(model, BuyAnimalActionState)
            assert model.animal == animal
        with pytest.raises(ValidationError):
            parse({"type": "BUY_ANIMAL", "animal": "PIG", "count": 1})


class TestSell:
    """Tests for `SellActionState` — item literal across all products."""

    @pytest.mark.parametrize(
        "item",
        ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"],
    )
    def test_accepts_every_product(self, item):
        model = parse({"type": "SELL", "item": item, "count": 1})
        assert isinstance(model, SellActionState)
        assert model.item == item

    def test_rejects_non_product(self):
        with pytest.raises(ValidationError):
            parse({"type": "SELL", "item": "GOOSE", "count": 1})


class TestCountConstraints:
    """Tests for count constraints — gt=0 on every action that carries a count."""

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
    def test_count_must_be_positive(self, payload):
        with pytest.raises(ValidationError):
            parse(payload)


class TestUnknownType:
    """Tests for unknown discriminator tags rejected at the union level."""

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
    def test_unknown_type_rejected(self, payload):
        with pytest.raises(ValidationError):
            parse(payload)


class TestNoArgActions:
    """Tests for no-arg actions — they carry only the `type` field."""

    def test_carry_only_type(self):
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


class TestRoundTrip:
    """Tests for round-trip — a model built directly dumps to the same payload."""

    def test_buy_seed(self):
        model = BuySeedActionState(type="BUY_SEED", crop="MELON", count=5)
        dumped = model.model_dump()
        assert dumped == {"type": "BUY_SEED", "crop": "MELON", "count": 5}
        # And the dumped dict re-validates through the union.
        assert isinstance(parse(dumped), BuySeedActionState)

    def test_sell(self):
        model = SellActionState(type="SELL", item="WOOL", count=12)
        dumped = model.model_dump()
        assert dumped == {"type": "SELL", "item": "WOOL", "count": 12}
        assert isinstance(parse(dumped), SellActionState)