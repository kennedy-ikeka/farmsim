"""Tests for action scoring — cost / reward / risk / final score."""
from src.domains.player.player import Player
from src.domains.player.valid_actions import get_valid_actions
from src.domains.player.scoring import (
    available_resources,
    action_resource_usage,
    action_resource_gain,
    cost_score,
    reward_score,
    future_cost_score,
    score_action,
    score_valid_actions,
)
from src.models.action import (
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
    PassActionState,
    PlaceActionState,
    PlantActionState,
    SellActionState,
    BuildCoopActionState,
    BuildPastureActionState,
    WaterActionState,
)
from src.models.farm import AnimalState, PlantState
from src.models.player import ResourceWeights
from src.utils.config import EPISODE_STEPS


class TestAvailableResources:
    def test_defaults(self):
        """Default player: money=0, 100 empty tiles, 0 seeds/animals/hands."""
        player = Player().build()
        avail = available_resources(player)
        assert avail["MONEY"] == 0.0
        assert avail["STEP"] == float(EPISODE_STEPS)
        assert avail["SEED"] == 0.0
        assert avail["LAND"] == 100.0  # 10x10 all empty
        assert avail["ANIMAL"] == 0.0
        assert avail["HAND"] == 0.0

    def test_money(self):
        player = Player().build(money=2500)
        assert available_resources(player)["MONEY"] == 2500.0

    def test_step_remaining(self):
        player = Player().build(step=100)
        assert available_resources(player)["STEP"] == float(EPISODE_STEPS - 100)

    def test_seeds(self):
        # Economic value: 3 WHEAT (10 each) + 2 MELON (80 each) = 30 + 160 = 190
        player = Player().build(seeds={"WHEAT": 3, "MELON": 2})
        assert available_resources(player)["SEED"] == 190.0

    def test_empty_tiles_excludes_occupied(self):
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        assert available_resources(player)["LAND"] == 0.0  # 1x1, occupied

    def test_animals_in_shed(self):
        # Economic value: 2 GOOSE (300 each) + 1 COW (400) = 600 + 400 = 1000
        player = Player().build(shed={"GOOSE": 2, "COW": 1})
        assert available_resources(player)["ANIMAL"] == 1000.0

    def test_animals_on_tiles(self):
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        # 1 GOOSE on tile = 300
        assert available_resources(player)["ANIMAL"] == 300.0

    def test_hands(self):
        player = Player().build(farmer=(5, 5), hands=[[4, 4], [5, 4]])
        assert available_resources(player)["HAND"] == 2.0


class TestActionResourceUsage:
    def test_every_action_uses_one_step(self):
        player = Player().build()
        for action in [PassActionState(), MoveActionState(type="NORTH"),
                       BuildCoopActionState(type="BUILD_COOP")]:
            assert action_resource_usage(action, player)["STEP"] == 1.0

    def test_plant_uses_seed_cost_and_land(self):
        player = Player().build(seeds={"WHEAT": 5})
        usage = action_resource_usage(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert usage["SEED"] == 10.0  # WHEAT seed_cost (economic, not raw count)
        assert usage["LAND"] == 1.0   # occupies an empty tile
        assert "MONEY" not in usage

    def test_build_uses_one_land(self):
        player = Player().build()
        usage = action_resource_usage(BuildCoopActionState(type="BUILD_COOP"), player)
        assert usage["LAND"] == 1.0

    def test_buy_seed_uses_money(self):
        player = Player().build(money=3000)
        action = BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1)
        usage = action_resource_usage(action, player)
        # WHEAT seed_cost = 10
        assert usage["MONEY"] == 10.0

    def test_buy_animal_uses_money(self):
        player = Player().build(money=3000)
        action = BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1)
        usage = action_resource_usage(action, player)
        # GOOSE cost = 300
        assert usage["MONEY"] == 300.0

    def test_hire_uses_fib_money(self):
        player = Player().build(money=3000, hires_today=0)
        usage = action_resource_usage(HireActionState(type="HIRE"), player)
        # fib(0) = 1
        assert usage["MONEY"] == 1.0

    def test_hire_cost_escalates(self):
        player = Player().build(money=3000, hires_today=3)
        usage = action_resource_usage(HireActionState(type="HIRE"), player)
        # fib(3) = 3
        assert usage["MONEY"] == 3.0

    def test_buy_land_uses_quadrant_cost(self):
        player = Player().build(money=3000, unlocked_quadrants=["NW"])
        usage = action_resource_usage(BuyLandActionState(type="BUY_LAND"), player)
        # Next quadrant is NE, cost = 1000
        assert usage["MONEY"] == 1000.0

    def test_pass_only_step(self):
        player = Player().build()
        usage = action_resource_usage(PassActionState(), player)
        assert usage == {"STEP": 1.0}

    def test_feed_uses_wheat_money(self):
        """FEED consumes 1 WHEAT from shed, valued at market price (=1 in build)."""
        player = Player().build(money=3000)
        usage = action_resource_usage(FeedActionState(type="FEED"), player)
        assert usage["MONEY"] == 1.0  # prices.WHEAT = 1 in Player().build
        assert usage["STEP"] == 1.0

    def test_fertilize_uses_fertilizer_money(self):
        """FERTILIZE consumes 1 FERTILIZER from shed, valued at market price (=1)."""
        player = Player().build(money=3000)
        usage = action_resource_usage(FertilizeActionState(type="FERTILIZE"), player)
        assert usage["MONEY"] == 1.0  # prices.FERTILIZER = 1 in Player().build
        assert usage["STEP"] == 1.0


class TestCostScore:
    def test_pass_cost_is_step_weight(self):
        """PASS uses 1 step; cost = 1 * step_weight (raw usage × weight)."""
        player = Player().build()
        cost = cost_score(PassActionState(), player)
        expected = 1.0 * player.private.config.resource_weights.STEP
        assert abs(cost - expected) < 1e-9

    def test_plant_cost_is_seed_plus_land_plus_step(self):
        """PLANT uses SEED (economic=10) + LAND (1) + STEP (1); cost = sum of usage × weight."""
        player = Player().build(seeds={"WHEAT": 5})
        cost = cost_score(PlantActionState(type="PLANT", crop="WHEAT"), player)
        w = player.private.config.resource_weights
        expected = 10.0 * w.SEED + 1.0 * w.LAND + 1.0 * w.STEP
        assert abs(cost - expected) < 1e-9

    def test_buy_seed_cost_is_money_plus_step(self):
        """BUY_SEED WHEAT costs MONEY=10 + STEP=1; cost = 10*MONEY_w + 1*STEP_w."""
        player = Player().build(money=3000)
        cost = cost_score(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1), player)
        w = player.private.config.resource_weights
        expected = 10.0 * w.MONEY + 1.0 * w.STEP
        assert abs(cost - expected) < 1e-9

    def test_build_cost_is_land_plus_step(self):
        """BUILD_COOP uses LAND=1 + STEP=1; cost = 1*LAND_w + 1*STEP_w."""
        player = Player().build()
        cost = cost_score(BuildCoopActionState(type="BUILD_COOP"), player)
        w = player.private.config.resource_weights
        expected = 1.0 * w.LAND + 1.0 * w.STEP
        assert abs(cost - expected) < 1e-9

    def test_custom_weights_change_cost(self):
        """Bumping STEP weight from 1.0 to 5.0 scales the step term of PLANT cost by 5.

        PLANT WHEAT: SEED=10, LAND=1, STEP=1. Base cost = 10+1+1 = 12;
        heavy (STEP=5) cost = 10+1+5 = 16.
        """
        player = Player().build(seeds={"WHEAT": 5})
        heavy = Player().build(
            seeds={"WHEAT": 5},
            resource_weights=ResourceWeights(STEP=5.0),
        )
        base = cost_score(PlantActionState(type="PLANT", crop="WHEAT"), player)
        bumped = cost_score(PlantActionState(type="PLANT", crop="WHEAT"), heavy)
        assert abs(base - 12.0) < 1e-9
        assert abs(bumped - 16.0) < 1e-9
        assert bumped > base


class TestScoreAction:
    def test_final_score_is_negative_cost(self):
        """With reward=0 and future_value=0: score = reward - cost = -cost.

        Uses PASS (which has no gain) — PLANT now has a reward so it no longer
        satisfies the reward=0 condition.
        """
        player = Player().build()
        scored = score_action(PassActionState(), player)
        assert abs(scored.score - (-scored.cost_score)) < 1e-9
        assert scored.reward_score == 0.0
        assert scored.future_cost_score == 0.0

    def test_scored_action_wraps_original(self):
        action = PassActionState()
        player = Player().build()
        scored = score_action(action, player)
        assert scored.action == action


class TestScoreValidActions:
    def test_returns_scored_valid_steps_state(self):
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        valid = get_valid_actions(player)
        scored = score_valid_actions(valid, player)
        assert len(scored.farmer) == len(valid.farmer)
        assert len(scored.hands) == len(valid.hands)
        assert len(scored.market) == len(valid.market)

    def test_all_scored_actions_have_nonnegative_reward(self):
        """Reward scores are non-negative (gains are never negative)."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        scored = score_valid_actions(get_valid_actions(player), player)
        for s in scored.farmer + scored.market:
            assert s.reward_score >= 0.0

    def test_sell_action_has_positive_final_score_when_broke(self):
        """SELL generates MONEY reward; when broke the reward dominates cost.

        Player().build sets all prices to 1 (reward=1, cost=1 → score=0), so we
        set a real WHEAT price (5) to make reward (5) exceed the step cost (1).
        """
        player = Player().build(money=0, shed={"WHEAT": 1}, market_prices={"WHEAT": 5})
        scored = score_valid_actions(get_valid_actions(player), player)
        sells = [s for s in scored.market if s.action.type == "SELL"]
        assert sells, "expected at least one SELL action"
        for s in sells:
            assert s.reward_score > 0.0
            assert s.score > 0.0

    def test_smoke_test_with_rich_player(self):
        """A rich player with seeds gets scored actions including BUY_SEED and PLANT."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        scored = score_valid_actions(get_valid_actions(player), player)
        farmer_types = {s.action.type for s in scored.farmer}
        market_types = {s.action.type for s in scored.market}
        assert "PASS" in farmer_types
        assert "PLANT" in farmer_types
        assert "BUY_SEED" in market_types


class TestActionResourceGain:
    def test_sell_gains_money(self):
        """SELL gains MONEY = count * price. Player().build sets all prices to 1."""
        player = Player().build(money=3000, shed={"WHEAT": 1})
        gain = action_resource_gain(SellActionState(type="SELL", item="WHEAT", count=1), player)
        assert gain == {"MONEY": 1.0}

    def test_buy_seed_gains_seed_value(self):
        """BUY_SEED gains SEED = count * seed_cost (economic value). WHEAT seed_cost=10."""
        player = Player().build(money=3000)
        gain = action_resource_gain(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1), player)
        assert gain == {"SEED": 10.0}

    def test_buy_animal_gains_animal_value(self):
        """BUY_ANIMAL gains ANIMAL = count * cost. GOOSE cost=300."""
        player = Player().build(money=3000)
        gain = action_resource_gain(BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1), player)
        assert gain == {"ANIMAL": 300.0}

    def test_hire_gains_hand(self):
        player = Player().build(money=3000, hires_today=0)
        gain = action_resource_gain(HireActionState(type="HIRE"), player)
        assert gain == {"HAND": 1.0}

    def test_buy_land_gains_locked_tiles(self):
        """BUY_LAND gains LAND = LOCKED tiles in the next quadrant (NE = 25 on 10x10)."""
        player = Player().build(money=3000, unlocked_quadrants=["NW"])
        gain = action_resource_gain(BuyLandActionState(type="BUY_LAND"), player)
        assert gain == {"LAND": 25.0}

    def test_harvest_gains_crop_value(self):
        """HARVEST gains MONEY = yield_units * price (WHEAT price=1 in build)."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100, yield_units=3)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        gain = action_resource_gain(HarvestActionState(type="HARVEST"), player)
        assert gain == {"MONEY": 3.0}

    def test_collect_fertilizer_gains_fertilizer_value(self):
        """COLLECT_FERTILIZER gains MONEY = FERTILIZER price (=1 in build)."""
        coop = AnimalState(kind="COOP", animal="GOOSE", fertilizer_available=1)
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        gain = action_resource_gain(CollectFertilizerActionState(type="COLLECT_FERTILIZER"), player)
        assert gain == {"MONEY": 1.0}

    def test_transfer_actions_gain_nothing(self):
        """MOVE and PASS have no resource gain (positioning / no-op).

        PLANT and BUILD_COOP now have state-transition rewards, so they're
        tested separately.
        """
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        for action in [MoveActionState(type="NORTH"),
                       PassActionState()]:
            assert action_resource_gain(action, player) == {}

    def test_harvest_no_gain_when_no_yield(self):
        """A plant with yield_units=0 gives no HARVEST gain."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100, yield_units=0)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        assert action_resource_gain(HarvestActionState(type="HARVEST"), player) == {}

    def test_collect_fertilizer_no_gain_when_unavailable(self):
        """An animal tile with no fertilizer_available gives no gain."""
        coop = AnimalState(kind="COOP", animal="GOOSE", fertilizer_available=0)
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        assert action_resource_gain(CollectFertilizerActionState(type="COLLECT_FERTILIZER"), player) == {}

    # ---------------------------------------------------------------------------
    # Enabler action rewards — state-transition value.
    # ---------------------------------------------------------------------------

    def test_plant_gains_potential_harvest_value(self):
        """PLANT gains MONEY = max_yield * price (WHEAT: 6 * 1 = 6 in build)."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        gain = action_resource_gain(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert gain == {"MONEY": 6.0}  # max_yield=6, price=1

    def test_build_coop_gains_egg_value(self):
        """BUILD_COOP gains MONEY = prices.EGG (=1 in build)."""
        player = Player().build(money=3000)
        gain = action_resource_gain(BuildCoopActionState(type="BUILD_COOP"), player)
        assert gain == {"MONEY": 1.0}

    def test_build_pasture_gains_best_product_value(self):
        """BUILD_PASTURE gains MONEY = max(prices.MILK, prices.WOOL) (=1 in build)."""
        player = Player().build(money=3000)
        gain = action_resource_gain(BuildPastureActionState(type="BUILD_PASTURE"), player)
        assert gain == {"MONEY": 1.0}  # both MILK and WOOL are 1 in build

    def test_feed_gains_product_value(self):
        """FEED on a GOOSE tile gains MONEY = prices.EGG (=1 in build)."""
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        gain = action_resource_gain(FeedActionState(type="FEED"), player)
        assert gain == {"MONEY": 1.0}

    def test_feed_no_gain_when_no_animal(self):
        """FEED on an empty tile gives no gain."""
        player = Player().build(farmer=(0, 0), tiles=[[None]])
        assert action_resource_gain(FeedActionState(type="FEED"), player) == {}

    def test_care_gains_product_value(self):
        """CARE on a GOOSE tile gains MONEY = prices.EGG (=1 in build)."""
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        gain = action_resource_gain(CareActionState(type="CARE"), player)
        assert gain == {"MONEY": 1.0}

    def test_care_no_gain_when_no_animal(self):
        """CARE on an empty tile gives no gain."""
        player = Player().build(farmer=(0, 0), tiles=[[None]])
        assert action_resource_gain(CareActionState(type="CARE"), player) == {}

    def test_fertilize_gains_crop_value(self):
        """FERTILIZE on a WHEAT plant gains MONEY = prices.WHEAT (=1 in build)."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        gain = action_resource_gain(FertilizeActionState(type="FERTILIZE"), player)
        assert gain == {"MONEY": 1.0}

    def test_fertilize_no_gain_when_no_plant(self):
        """FERTILIZE on an empty tile gives no gain."""
        player = Player().build(farmer=(0, 0), tiles=[[None]])
        assert action_resource_gain(FertilizeActionState(type="FERTILIZE"), player) == {}

    def test_water_gains_crop_value(self):
        """WATER on a WHEAT plant gains MONEY = prices.WHEAT (=1 in build)."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        gain = action_resource_gain(WaterActionState(type="WATER"), player)
        assert gain == {"MONEY": 1.0}

    def test_water_no_gain_when_no_plant(self):
        """WATER on an empty tile gives no gain."""
        player = Player().build(farmer=(0, 0), tiles=[[None]])
        assert action_resource_gain(WaterActionState(type="WATER"), player) == {}

    def test_dig_gains_one_land(self):
        """DIG frees a tile back to empty → gains LAND = 1.0."""
        player = Player().build(farmer=(0, 0))
        gain = action_resource_gain(DigActionState(type="DIG"), player)
        assert gain == {"LAND": 1.0}

    def test_place_animal_gains_product_value(self):
        """PLACE a GOOSE gains MONEY = prices.EGG (=1 in build)."""
        player = Player().build(money=3000)
        gain = action_resource_gain(
            PlaceActionState(type="PLACE", item="GOOSE", count=1), player
        )
        assert gain == {"MONEY": 1.0}

    def test_place_shed_drop_gains_nothing(self):
        """PLACE a non-animal item (shed drop) gains nothing."""
        player = Player().build(money=3000)
        gain = action_resource_gain(
            PlaceActionState(type="PLACE", item="WHEAT", count=1), player
        )
        assert gain == {}

    def test_buy_product_gains_product_value(self):
        """BUY_PRODUCT gains MONEY = prices[item] * count (=1*2 in build)."""
        player = Player().build(money=3000)
        gain = action_resource_gain(
            BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=2), player
        )
        assert gain == {"MONEY": 2.0}


class TestRewardScore:
    def test_sell_reward_proportional_to_price(self):
        """SELL WHEAT (price=1) when broke: reward = (1 / max(0,1)) * MONEY weight = 1."""
        player = Player().build(money=0, shed={"WHEAT": 1})
        reward = reward_score(SellActionState(type="SELL", item="WHEAT", count=1), player)
        assert abs(reward - 1.0) < 1e-9

    def test_buy_seed_reward_scales_with_value(self):
        """BUY_SEED WHEAT gains 10 seed-value; with 0 seeds → reward = 10 * SEED weight."""
        player = Player().build(money=3000, seeds={"WHEAT": 0})
        reward = reward_score(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1), player)
        assert abs(reward - 10.0) < 1e-9

    def test_sell_reward_is_constant_regardless_of_money(self):
        """Reward is now raw gain × weight (no /available divisor), so it does
        not diminish as money grows: SELL WHEAT (price=1) rewards 1.0 whether
        broke or rich.
        """
        broke = Player().build(money=0, shed={"WHEAT": 1})
        rich = Player().build(money=3000, shed={"WHEAT": 1})
        r_broke = reward_score(SellActionState(type="SELL", item="WHEAT", count=1), broke)
        r_rich = reward_score(SellActionState(type="SELL", item="WHEAT", count=1), rich)
        assert abs(r_broke - 1.0) < 1e-9
        assert abs(r_rich - 1.0) < 1e-9

    def test_custom_weights_change_reward(self):
        """Bumping MONEY weight from 1.0 to 5.0 scales the SELL reward 5x."""
        base = Player().build(money=0, shed={"WHEAT": 1})
        heavy = Player().build(
            money=0, shed={"WHEAT": 1},
            resource_weights=ResourceWeights(MONEY=5.0),
        )
        r_base = reward_score(SellActionState(type="SELL", item="WHEAT", count=1), base)
        r_heavy = reward_score(SellActionState(type="SELL", item="WHEAT", count=1), heavy)
        assert abs(r_heavy - r_base * 5.0) < 1e-9

    def test_move_and_pass_reward_is_zero(self):
        """MOVE and PASS have no gain → reward = 0."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        assert reward_score(MoveActionState(type="NORTH"), player) == 0.0
        assert reward_score(PassActionState(), player) == 0.0


class TestFinalScoreWithReward:
    def test_final_score_is_reward_minus_cost(self):
        """With future_value=0: score = reward - cost. Uses SELL when broke (reward=1, cost=1)."""
        player = Player().build(money=0, shed={"WHEAT": 1})
        scored = score_action(SellActionState(type="SELL", item="WHEAT", count=1), player)
        step_cost = 1.0 * player.private.config.resource_weights.STEP
        expected = scored.reward_score - scored.cost_score
        assert abs(scored.score - expected) < 1e-9
        assert abs(scored.cost_score - step_cost) < 1e-9
        assert scored.reward_score == 1.0