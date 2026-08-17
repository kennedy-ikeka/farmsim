"""Tests for action scoring — cost / reward / risk / final score."""
from src.domains.player.player import Player
from src.domains.player.valid_actions import get_valid_actions
from src.domains.player.scoring import (
    action_resource_usage,
    action_resource_gain,
    action_future_gain,
    action_future_usage,
    cost_score,
    reward_score,
    future_cost_score,
    future_reward_score,
    score_action,
    score_valid_actions,
    update_resource_weights,
)
from src.domains.farm.scoring import available_resources
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
from src.models.resource import ResourceState
from src.utils.config import EPISODE_STEPS


class TestAvailableResources:
    def test_defaults(self):
        """Default player: money=0, 100 empty tiles, 0 seeds/animals/hands."""
        player = Player().build()
        avail = available_resources(player)
        assert avail.MONEY == 0.0
        assert avail.STEP == float(EPISODE_STEPS)
        assert avail.SEED == 0.0
        assert avail.LAND == 100.0  # 10x10 all empty
        assert avail.ANIMAL == 0.0
        assert avail.HAND == 0.0

    def test_money(self):
        player = Player().build(money=2500)
        assert available_resources(player).MONEY == 2500.0

    def test_step_remaining(self):
        player = Player().build(step=100)
        assert available_resources(player).STEP == float(EPISODE_STEPS - 100)

    def test_seeds(self):
        # Economic value: 3 WHEAT (10 each) + 2 MELON (80 each) = 30 + 160 = 190
        player = Player().build(seeds={"WHEAT": 3, "MELON": 2})
        assert available_resources(player).SEED == 190.0

    def test_empty_tiles_excludes_occupied(self):
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        assert available_resources(player).LAND == 0.0  # 1x1, occupied

    def test_animals_in_shed(self):
        # Economic value: 2 GOOSE (300 each) + 1 COW (400) = 600 + 400 = 1000
        player = Player().build(shed={"GOOSE": 2, "COW": 1})
        assert available_resources(player).ANIMAL == 1000.0

    def test_animals_on_tiles(self):
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        # 1 GOOSE on tile = 300
        assert available_resources(player).ANIMAL == 300.0

    def test_hands(self):
        player = Player().build(farmer=(5, 5), hands=[[4, 4], [5, 4]])
        assert available_resources(player).HAND == 2.0


class TestActionResourceUsage:
    def test_every_action_uses_one_step(self):
        player = Player().build()
        for action in [PassActionState(), MoveActionState(type="NORTH"),
                       BuildCoopActionState(type="BUILD_COOP")]:
            assert action_resource_usage(action, player).STEP == 1.0

    def test_plant_uses_seed_cost_and_land(self):
        player = Player().build(seeds={"WHEAT": 5})
        usage = action_resource_usage(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert usage.SEED == 10.0  # WHEAT seed_cost (economic, not raw count)
        assert usage.LAND == 1.0   # occupies an empty tile
        assert usage.MONEY == 0.0  # PLANT consumes no money

    def test_build_uses_one_land(self):
        player = Player().build()
        usage = action_resource_usage(BuildCoopActionState(type="BUILD_COOP"), player)
        assert usage.LAND == 1.0

    def test_buy_seed_uses_money(self):
        player = Player().build(money=3000)
        action = BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1)
        usage = action_resource_usage(action, player)
        # WHEAT seed_cost = 10
        assert usage.MONEY == 10.0

    def test_buy_animal_uses_money(self):
        player = Player().build(money=3000)
        action = BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1)
        usage = action_resource_usage(action, player)
        # GOOSE cost = 300
        assert usage.MONEY == 300.0

    def test_hire_uses_fib_money(self):
        player = Player().build(money=3000, hires_today=0)
        usage = action_resource_usage(HireActionState(type="HIRE"), player)
        # fib(0) = 1
        assert usage.MONEY == 1.0

    def test_hire_cost_escalates(self):
        player = Player().build(money=3000, hires_today=3)
        usage = action_resource_usage(HireActionState(type="HIRE"), player)
        # fib(3) = 3
        assert usage.MONEY == 3.0

    def test_buy_land_uses_quadrant_cost(self):
        player = Player().build(money=3000, unlocked_quadrants=["NW"])
        usage = action_resource_usage(BuyLandActionState(type="BUY_LAND"), player)
        # Next quadrant is NE, cost = 1000
        assert usage.MONEY == 1000.0

    def test_pass_only_step(self):
        player = Player().build()
        usage = action_resource_usage(PassActionState(), player)
        assert usage == ResourceState(STEP=1.0)

    def test_feed_uses_wheat_money(self):
        """FEED consumes 1 WHEAT from shed, valued at market price (=1 in build)."""
        player = Player().build(money=3000)
        usage = action_resource_usage(FeedActionState(type="FEED"), player)
        assert usage.MONEY == 1.0  # prices.WHEAT = 1 in Player().build
        assert usage.STEP == 1.0

    def test_fertilize_uses_fertilizer_money(self):
        """FERTILIZE consumes 1 FERTILIZER from shed, valued at market price (=1)."""
        player = Player().build(money=3000)
        usage = action_resource_usage(FertilizeActionState(type="FERTILIZE"), player)
        assert usage.MONEY == 1.0  # prices.FERTILIZER = 1 in Player().build
        assert usage.STEP == 1.0


class TestCostScore:
    def test_pass_cost_is_step_weight(self):
        """PASS uses 1 step; cost = (1 / available_step) * step_weight."""
        player = Player().build()
        cost = cost_score(PassActionState(), player)
        w = player.private.config.resource_weights
        avail = available_resources(player)
        expected = (1.0 / max(avail.STEP, 1.0)) * w.STEP
        assert abs(cost - expected) < 1e-9

    def test_plant_cost_is_seed_plus_land_plus_step(self):
        """PLANT uses SEED (economic=10) + LAND (1) + STEP (1);
        cost = sum of (usage / available) * weight."""
        player = Player().build(seeds={"WHEAT": 5})
        cost = cost_score(PlantActionState(type="PLANT", crop="WHEAT"), player)
        w = player.private.config.resource_weights
        avail = available_resources(player)
        expected = ((10.0 / max(avail.SEED, 1.0)) * w.SEED
                    + (1.0 / max(avail.LAND, 1.0)) * w.LAND
                    + (1.0 / max(avail.STEP, 1.0)) * w.STEP)
        assert abs(cost - expected) < 1e-9

    def test_buy_seed_cost_is_money_plus_step(self):
        """BUY_SEED WHEAT costs MONEY=10 + STEP=1;
        cost = (10/available_money)*MONEY_w + (1/available_step)*STEP_w."""
        player = Player().build(money=3000)
        cost = cost_score(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1), player)
        w = player.private.config.resource_weights
        avail = available_resources(player)
        expected = ((10.0 / max(avail.MONEY, 1.0)) * w.MONEY
                    + (1.0 / max(avail.STEP, 1.0)) * w.STEP)
        assert abs(cost - expected) < 1e-9

    def test_build_cost_is_land_plus_step(self):
        """BUILD_COOP uses LAND=1 + STEP=1;
        cost = (1/available_land)*LAND_w + (1/available_step)*STEP_w."""
        player = Player().build()
        cost = cost_score(BuildCoopActionState(type="BUILD_COOP"), player)
        w = player.private.config.resource_weights
        avail = available_resources(player)
        expected = ((1.0 / max(avail.LAND, 1.0)) * w.LAND
                    + (1.0 / max(avail.STEP, 1.0)) * w.STEP)
        assert abs(cost - expected) < 1e-9

    def test_custom_weights_change_cost(self):
        """Bumping STEP weight scales the step term of PLANT cost.

        Scarcity-weighted: cost = (10/avail_SEED)*SEED_w + (1/avail_LAND)*LAND_w
        + (1/avail_STEP)*STEP_w. Bumping STEP_w from 1→5 only changes the last term.
        """
        player = Player().build(seeds={"WHEAT": 5})
        heavy = Player().build(
            seeds={"WHEAT": 5},
            resource_weights=ResourceWeights(STEP=5.0),
        )
        base = cost_score(PlantActionState(type="PLANT", crop="WHEAT"), player)
        bumped = cost_score(PlantActionState(type="PLANT", crop="WHEAT"), heavy)
        avail = available_resources(player)
        step_term_base = (1.0 / max(avail.STEP, 1.0)) * 1.0
        step_term_heavy = (1.0 / max(avail.STEP, 1.0)) * 5.0
        assert abs(base - bumped + step_term_heavy - step_term_base) < 1e-9
        assert bumped > base


class TestScoreAction:
    def test_final_score_is_negative_cost(self):
        """With reward=0 and future_value=0: score = reward - cost = -cost.

        Uses PASS (no gain, no future value). Enabler actions like PLANT have
        future_value > 0, so they don't satisfy this condition.
        """
        player = Player().build()
        scored = score_action(PassActionState(), player)
        assert abs(scored.score - (-scored.cost_score)) < 1e-9
        assert scored.reward_score == 0.0
        assert scored.future_cost_score == 0.0

    def test_plant_final_score_is_future_minus_cost(self):
        """PLANT WHEAT at day 0 with real prices: reward=0 (enabler),
        scarcity-weighted cost and future scores. Verifies the formula
        score = (reward - cost) + (future_reward - future_cost) * discount.
        """
        player = Player().build(
            money=3000, seeds={"WHEAT": 5},
            market_prices={"WHEAT": 25},
        )
        scored = score_action(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert scored.reward_score == 0.0          # enabler: no immediate gain
        # Verify the formula holds with the scarcity-weighted sub-scores.
        expected = (scored.reward_score - scored.cost_score) + (
            scored.future_reward_score - scored.future_cost_score
        ) * player.private.config.score_weights.FUTURE_DISCOUNT_RATE
        assert abs(scored.score - expected) < 1e-9
        # PLANT is an enabler with positive future value → score should be positive.
        assert scored.score > 0.0

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

        With scarcity weighting: selling when money=0 gives reward = price/(0+price)
        = 1.0 (maximal marginal value). The produce cost per unit is 1/available_produce,
        so having 10 WHEAT makes each unit cheap to sell (1/10 = 0.1) while the
        money reward is 1.0 → score > 0.
        """
        player = Player().build(money=0, shed={"WHEAT": 10}, market_prices={"WHEAT": 5})
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
        assert gain == ResourceState(MONEY=1.0)

    def test_buy_seed_gains_seed_value(self):
        """BUY_SEED gains SEED = count * seed_cost (economic value). WHEAT seed_cost=10."""
        player = Player().build(money=3000)
        gain = action_resource_gain(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1), player)
        assert gain == ResourceState(SEED=10.0)

    def test_buy_animal_gains_animal_value(self):
        """BUY_ANIMAL gains ANIMAL = count * cost. GOOSE cost=300."""
        player = Player().build(money=3000)
        gain = action_resource_gain(BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1), player)
        assert gain == ResourceState(ANIMAL=300.0)

    def test_hire_gains_hand(self):
        player = Player().build(money=3000, hires_today=0)
        gain = action_resource_gain(HireActionState(type="HIRE"), player)
        assert gain == ResourceState(HAND=1.0)

    def test_buy_land_gains_locked_tiles(self):
        """BUY_LAND gains LAND = LOCKED tiles in the next quadrant (NE = 25 on 10x10)."""
        player = Player().build(money=3000, unlocked_quadrants=["NW"])
        gain = action_resource_gain(BuyLandActionState(type="BUY_LAND"), player)
        assert gain == ResourceState(LAND=25.0)

    def test_harvest_gains_crop_value(self):
        """HARVEST gains MONEY = yield_units * price and PRODUCE = yield_units (WHEAT price=1 in build)."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100, yield_units=3)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        gain = action_resource_gain(HarvestActionState(type="HARVEST"), player)
        assert gain == ResourceState(MONEY=3.0, PRODUCE=3.0)

    def test_collect_fertilizer_gains_fertilizer_value(self):
        """COLLECT_FERTILIZER gains MONEY = FERTILIZER price and PRODUCE = 1 (=1 in build)."""
        coop = AnimalState(kind="COOP", animal="GOOSE", fertilizer_available=1)
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        gain = action_resource_gain(CollectFertilizerActionState(type="COLLECT_FERTILIZER"), player)
        assert gain == ResourceState(MONEY=1.0, PRODUCE=1.0)

    def test_transfer_actions_gain_nothing(self):
        """MOVE and PASS have no resource gain (positioning / no-op).

        PLANT and BUILD_COOP now have state-transition rewards, so they're
        tested separately.
        """
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        for action in [MoveActionState(type="NORTH"),
                       PassActionState()]:
            assert action_resource_gain(action, player) == ResourceState()

    def test_harvest_no_gain_when_no_yield(self):
        """A plant with yield_units=0 gives no HARVEST gain."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100, yield_units=0)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        assert action_resource_gain(HarvestActionState(type="HARVEST"), player) == ResourceState()

    def test_collect_fertilizer_no_gain_when_unavailable(self):
        """An animal tile with no fertilizer_available gives no gain."""
        coop = AnimalState(kind="COOP", animal="GOOSE", fertilizer_available=0)
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        assert action_resource_gain(CollectFertilizerActionState(type="COLLECT_FERTILIZER"), player) == ResourceState()

    # ---------------------------------------------------------------------------
    # Enabler action immediate gains — these are now EMPTY; their deferred
    # payoff lives in `action_future_gain` (see TestActionFutureGain).
    # ---------------------------------------------------------------------------

    def test_plant_gains_nothing_immediate(self):
        """PLANT has no immediate resource gain; its payoff is deferred to HARVEST/SELL."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        gain = action_resource_gain(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert gain == ResourceState()

    def test_build_coop_gains_nothing_immediate(self):
        """BUILD_COOP has no immediate gain; payoff is deferred via PLACE/FEED/HARVEST."""
        player = Player().build(money=3000)
        gain = action_resource_gain(BuildCoopActionState(type="BUILD_COOP"), player)
        assert gain == ResourceState()

    def test_build_pasture_gains_nothing_immediate(self):
        """BUILD_PASTURE has no immediate gain; payoff is deferred via PLACE/FEED/HARVEST."""
        player = Player().build(money=3000)
        gain = action_resource_gain(BuildPastureActionState(type="BUILD_PASTURE"), player)
        assert gain == ResourceState()

    def test_feed_gains_nothing_immediate(self):
        """FEED on a GOOSE tile has no immediate gain; payoff is the deferred production."""
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        gain = action_resource_gain(FeedActionState(type="FEED"), player)
        assert gain == ResourceState()

    def test_feed_no_gain_when_no_animal(self):
        """FEED on an empty tile gives no gain."""
        player = Player().build(farmer=(0, 0), tiles=[[None]])
        assert action_resource_gain(FeedActionState(type="FEED"), player) == ResourceState()

    def test_care_gains_nothing_immediate(self):
        """CARE on a GOOSE tile has no immediate gain; payoff is the deferred bonus unit."""
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        gain = action_resource_gain(CareActionState(type="CARE"), player)
        assert gain == ResourceState()

    def test_care_no_gain_when_no_animal(self):
        """CARE on an empty tile gives no gain."""
        player = Player().build(farmer=(0, 0), tiles=[[None]])
        assert action_resource_gain(CareActionState(type="CARE"), player) == ResourceState()

    def test_fertilize_gains_nothing_immediate(self):
        """FERTILIZE on a WHEAT plant has no immediate gain; payoff is the deferred bonus yield."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        gain = action_resource_gain(FertilizeActionState(type="FERTILIZE"), player)
        assert gain == ResourceState()

    def test_fertilize_no_gain_when_no_plant(self):
        """FERTILIZE on an empty tile gives no gain."""
        player = Player().build(farmer=(0, 0), tiles=[[None]])
        assert action_resource_gain(FertilizeActionState(type="FERTILIZE"), player) == ResourceState()

    def test_water_gains_nothing_immediate(self):
        """WATER on a WHEAT plant has no immediate gain; payoff is the deferred yield unit."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        gain = action_resource_gain(WaterActionState(type="WATER"), player)
        assert gain == ResourceState()

    def test_water_no_gain_when_no_plant(self):
        """WATER on an empty tile gives no gain."""
        player = Player().build(farmer=(0, 0), tiles=[[None]])
        assert action_resource_gain(WaterActionState(type="WATER"), player) == ResourceState()

    def test_dig_gains_one_land(self):
        """DIG frees a tile back to empty → gains LAND = 1.0."""
        player = Player().build(farmer=(0, 0))
        gain = action_resource_gain(DigActionState(type="DIG"), player)
        assert gain == ResourceState(LAND=1.0)

    def test_place_animal_gains_produce_immediate(self):
        """PLACE a GOOSE deploys one productive unit → immediate PRODUCE = 1.0.
        The rest of the payoff is the deferred production (future_gain)."""
        player = Player().build(money=3000)
        gain = action_resource_gain(
            PlaceActionState(type="PLACE", item="GOOSE", count=1), player
        )
        assert gain == ResourceState(PRODUCE=1.0)

    def test_place_shed_drop_gains_nothing(self):
        """PLACE a non-animal item (shed drop) gains nothing."""
        player = Player().build(money=3000)
        gain = action_resource_gain(
            PlaceActionState(type="PLACE", item="WHEAT", count=1), player
        )
        assert gain == ResourceState()

    def test_buy_product_gains_product_value(self):
        """BUY_PRODUCT gains MONEY = prices[item] * count and PRODUCE = count (=1*2 in build)."""
        player = Player().build(money=3000)
        gain = action_resource_gain(
            BuyProductActionState(type="BUY_PRODUCT", item="WHEAT", count=2), player
        )
        assert gain == ResourceState(MONEY=2.0, PRODUCE=2.0)


class TestActionFutureGain:
    """Deferred payoff of enabler actions, valued at market prices.

    Player().build sets all prices to 1, so the MONEY values below are in
    "1 unit = 1 money" terms. Real prices are exercised in TestScoreAction.
    """

    def test_plant_future_gains_full_yield_value(self):
        """PLANT WHEAT at day 0 → 3 window days * price(1) = 3 MONEY, 3 PRODUCE future."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        gain = action_future_gain(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert gain == ResourceState(MONEY=3.0, PRODUCE=3.0)

    def test_plant_future_zero_when_late(self):
        """PLANT WHEAT at day 29 → window (days 31,32,33) past episode end → 0."""
        player = Player().build(money=3000, seeds={"WHEAT": 5}, step=29 * 24, day=29)
        gain = action_future_gain(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert gain == ResourceState()

    def test_plant_ongoing_crop_future_zero(self):
        """Ongoing crops (TOMATO) are not modeled → 0 future gain."""
        player = Player().build(money=3000, seeds={"TOMATO": 5})
        gain = action_future_gain(PlantActionState(type="PLANT", crop="TOMATO"), player)
        assert gain == ResourceState()

    def test_water_future_gains_one_unit(self):
        """WATER on an unfertilized WHEAT in window → 1 unit * price, 1 PRODUCE."""
        # planted_day=0, day=2 → dsp=2 in window [2,4].
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]], step=2 * 24, day=2)
        gain = action_future_gain(WaterActionState(type="WATER"), player)
        assert gain == ResourceState(MONEY=1.0, PRODUCE=1.0)

    def test_water_future_gains_two_when_fertilized(self):
        """WATER on a fertilized WHEAT in window → 2 units * price, 2 PRODUCE."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100,
                           fertilized_until_day=5)
        player = Player().build(farmer=(0, 0), tiles=[[plant]], step=2 * 24, day=2)
        gain = action_future_gain(WaterActionState(type="WATER"), player)
        assert gain == ResourceState(MONEY=2.0, PRODUCE=2.0)

    def test_water_future_zero_outside_window(self):
        """WATER outside the watering window adds no yield → 0 future gain."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]], step=1 * 24, day=1)
        gain = action_future_gain(WaterActionState(type="WATER"), player)
        assert gain == ResourceState()

    def test_fertilize_future_gains_window_bonus(self):
        """FERTILIZE on a fresh WHEAT (day 0) → bonus covers window days 2,3
        (day 4 is past fertilized_until_day=3) → 2 days * price = 2, 2 PRODUCE."""
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100)
        player = Player().build(farmer=(0, 0), tiles=[[plant]])
        gain = action_future_gain(FertilizeActionState(type="FERTILIZE"), player)
        assert gain == ResourceState(MONEY=2.0, PRODUCE=2.0)

    def test_build_coop_future_gains_goose_production(self):
        """BUILD_COOP at day 0 → GOOSE yield(54) * EGG(1) + fert_days(30) * FERTILIZER(1) = 84
        MONEY, 84 PRODUCE (54+30 product+fertilizer units)."""
        player = Player().build(money=3000)
        gain = action_future_gain(BuildCoopActionState(type="BUILD_COOP"), player)
        assert gain == ResourceState(MONEY=84.0, PRODUCE=84.0)

    def test_build_pasture_future_picks_best_animal(self):
        """BUILD_PASTURE at day 0 → max(COW net, SHEEP net). With flat-1 prices:
        COW = 36*1 + 30*1 = 66; SHEEP = 34*1 + 30*1 = 64 → 66 MONEY, 66 PRODUCE."""
        player = Player().build(money=3000)
        gain = action_future_gain(BuildPastureActionState(type="BUILD_PASTURE"), player)
        assert gain == ResourceState(MONEY=66.0, PRODUCE=66.0)

    def test_place_future_gains_animal_production(self):
        """PLACE GOOSE at day 0 → 54 * EGG(1) + 30 * FERTILIZER(1) = 84 MONEY, 84 PRODUCE."""
        player = Player().build(money=3000, shed={"GOOSE": 1})
        gain = action_future_gain(
            PlaceActionState(type="PLACE", item="GOOSE", count=1), player
        )
        assert gain == ResourceState(MONEY=84.0, PRODUCE=84.0)

    def test_place_shed_drop_future_empty(self):
        """PLACE a non-animal item has no deferred production → empty."""
        player = Player().build(money=3000, shed={"WHEAT": 1})
        gain = action_future_gain(
            PlaceActionState(type="PLACE", item="WHEAT", count=1), player
        )
        assert gain == ResourceState()

    def test_feed_future_gains_one_product_unit(self):
        """FEED on a GOOSE tile → 1 EGG * price(1) = 1, 1 PRODUCE."""
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        gain = action_future_gain(FeedActionState(type="FEED"), player)
        assert gain == ResourceState(MONEY=1.0, PRODUCE=1.0)

    def test_feed_future_empty_when_no_animal(self):
        coop = AnimalState(kind="COOP", animal=None)
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        assert action_future_gain(FeedActionState(type="FEED"), player) == ResourceState()

    def test_care_future_gains_one_product_unit(self):
        """CARE on a GOOSE tile → 1 EGG * price(1) = 1, 1 PRODUCE."""
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        gain = action_future_gain(CareActionState(type="CARE"), player)
        assert gain == ResourceState(MONEY=1.0, PRODUCE=1.0)

    def test_enabler_future_gain_empty_for_immediate_actions(self):
        """SELL / HARVEST / COLLECT_FERTILIZER / MOVE / PASS have no deferred gain."""
        player = Player().build(money=3000, shed={"WHEAT": 1})
        plant = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=100, yield_units=2)
        player2 = Player().build(farmer=(0, 0), tiles=[[plant]])
        for action in [SellActionState(type="SELL", item="WHEAT", count=1),
                       HarvestActionState(type="HARVEST"),
                       MoveActionState(type="NORTH"),
                       PassActionState()]:
            assert action_future_gain(action, player) == ResourceState(), action.type
        assert action_future_gain(HarvestActionState(type="HARVEST"), player2) == ResourceState()


class TestActionFutureUsage:
    def test_plant_future_usage_is_waters_plus_harvest_plus_sell(self):
        """PLANT WHEAT at day 0 → 3 future waters + 1 harvest + 1 sell = 5 steps."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        usage = action_future_usage(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert usage == ResourceState(STEP=5.0)

    def test_plant_future_usage_zero_when_late(self):
        """PLANT WHEAT at day 29 → no future window days → harvest+sell still
        counted = 2 steps (waters=0)."""
        player = Player().build(money=3000, seeds={"WHEAT": 5}, step=29 * 24, day=29)
        usage = action_future_usage(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert usage == ResourceState(STEP=2.0)  # waters=0, +harvest+sell

    def test_water_future_usage_is_harvest_plus_sell(self):
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        usage = action_future_usage(WaterActionState(type="WATER"), player)
        assert usage == ResourceState(STEP=2.0)

    def test_build_coop_future_usage_is_feed_wheat_plus_steps(self):
        """BUILD_COOP at day 0 → remaining_days=30. STEP = 1 place + 30 feed +
        30 care + 1 harvest + 1 sell + 30 collect = 93. MONEY = 30 * WHEAT(1) = 30.
        PRODUCE = 30 feed-wheat units consumed from the shed."""
        player = Player().build(money=3000)
        usage = action_future_usage(BuildCoopActionState(type="BUILD_COOP"), player)
        assert usage == ResourceState(STEP=93.0, MONEY=30.0, PRODUCE=30.0)

    def test_place_future_usage_is_feed_wheat_plus_steps(self):
        """PLACE GOOSE at day 0 → STEP = 30 feed + 30 care + 1 harvest + 1 sell +
        30 collect = 92. MONEY = 30 * WHEAT(1) = 30. PRODUCE = 30 feed-wheat units."""
        player = Player().build(money=3000, shed={"GOOSE": 1})
        usage = action_future_usage(PlaceActionState(type="PLACE", item="GOOSE", count=1), player)
        assert usage == ResourceState(STEP=92.0, MONEY=30.0, PRODUCE=30.0)

    def test_feed_future_usage_is_harvest_plus_sell(self):
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        usage = action_future_usage(FeedActionState(type="FEED"), player)
        assert usage == ResourceState(STEP=2.0)

    def test_care_future_usage_is_harvest_plus_sell(self):
        coop = AnimalState(kind="COOP", animal="GOOSE")
        player = Player().build(farmer=(0, 0), tiles=[[coop]])
        usage = action_future_usage(CareActionState(type="CARE"), player)
        assert usage == ResourceState(STEP=2.0)

    def test_immediate_actions_future_usage_empty(self):
        """SELL / PASS / HARVEST have no future usage."""
        player = Player().build(money=3000, shed={"WHEAT": 1})
        for action in [SellActionState(type="SELL", item="WHEAT", count=1),
                       PassActionState()]:
            assert action_future_usage(action, player) == ResourceState(), action.type


class TestRewardScore:
    def test_sell_reward_proportional_to_price(self):
        """SELL WHEAT (price=1) when broke: reward = (1 / max(0,1)) * MONEY weight = 1."""
        player = Player().build(money=0, shed={"WHEAT": 1})
        reward = reward_score(SellActionState(type="SELL", item="WHEAT", count=1), player)
        assert abs(reward - 1.0) < 1e-9

    def test_buy_seed_reward_scales_with_value(self):
        """BUY_SEED reward with diminishing returns: gain / (available + gain).

        With existing seeds (WHEAT=5 → avail.SEED=50), buying MELON (gain=80)
        gives higher reward than WHEAT (gain=10) because 80/(50+80) > 10/(50+10).
        """
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        r_wheat = reward_score(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1), player)
        r_melon = reward_score(BuySeedActionState(type="BUY_SEED", crop="MELON", count=1), player)
        avail = available_resources(player)
        w = player.private.config.resource_weights
        expected_wheat = (10.0 / max(avail.SEED + 10.0, 1.0)) * w.SEED
        expected_melon = (80.0 / max(avail.SEED + 80.0, 1.0)) * w.SEED
        assert abs(r_wheat - expected_wheat) < 1e-9
        assert abs(r_melon - expected_melon) < 1e-9
        assert r_melon > r_wheat  # higher value → higher reward

    def test_sell_reward_diminishes_as_money_grows(self):
        """Scarcity-weighted reward: selling when broke gives higher reward
        than selling when rich (marginal value of money is higher when poor).
        """
        broke = Player().build(money=0, shed={"WHEAT": 10})
        rich = Player().build(money=3000, shed={"WHEAT": 10})
        r_broke = reward_score(SellActionState(type="SELL", item="WHEAT", count=1), broke)
        r_rich = reward_score(SellActionState(type="SELL", item="WHEAT", count=1), rich)
        assert r_broke > r_rich  # selling is more valuable when broke

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
        """With future_value=0: score = reward - cost (scarcity-weighted).

        SELL when broke (money=0, 1 WHEAT): cost = (1/avail_step)*STEP_w +
        (1/avail_produce)*PRODUCE_w, reward = (1/(0+1))*MONEY_w = 1.0.
        """
        player = Player().build(money=0, shed={"WHEAT": 1})
        scored = score_action(SellActionState(type="SELL", item="WHEAT", count=1), player)
        w = player.private.config.resource_weights
        avail = available_resources(player)
        cost = ((1.0 / max(avail.STEP, 1.0)) * w.STEP
                + (1.0 / max(avail.PRODUCE, 1.0)) * w.PRODUCE)
        expected = scored.reward_score - scored.cost_score
        assert abs(scored.score - expected) < 1e-9
        assert abs(scored.cost_score - cost) < 1e-9
        assert scored.reward_score == 1.0  # 1 / max(0 + 1, 1) = 1.0
        assert scored.reward_score == 1.0


class TestUpdateResourceWeights:
    """Satiation-style weight update after play."""

    def test_empty_selected_leaves_weights_unchanged(self):
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        before = player.private.config.resource_weights.model_copy()
        update_resource_weights(player, [])
        assert player.private.config.resource_weights == before

    def test_driving_resources_get_lower_weights(self):
        """BUY_ANIMAL's immediate driver is ANIMAL (gain=cost, no usage).
        After the update ANIMAL drops below the untouched resources. PRODUCE
        is only a future driver → NOT satiated, stays at 1.0."""
        player = Player().build(money=3000)
        scored = score_action(
            BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1), player
        )
        update_resource_weights(player, [scored])
        w = player.private.config.resource_weights
        # ANIMAL was the immediate driver → reduced.
        assert w.ANIMAL < 1.0
        assert w.ANIMAL < w.STEP
        # PRODUCE is future-only → NOT satiated, stays max.
        assert w.PRODUCE == 1.0
        # MONEY is consumed (usage) but not gained → not a driver, unchanged.
        assert w.MONEY == 1.0

    def test_weights_normalized_to_0_1(self):
        """After update, every weight is in [0, 1] and at least one stays at 1.0
        (untouched resources). Satiation only reduces; no normalization now."""
        player = Player().build(money=3000)
        scored = score_action(
            BuyAnimalActionState(type="BUY_ANIMAL", animal="GOOSE", count=1), player
        )
        update_resource_weights(player, [scored])
        w = player.private.config.resource_weights
        values = [getattr(w, r) for r in type(w).model_fields]
        assert max(values) == 1.0
        assert all(0.0 <= v <= 1.0 for v in values)

    def test_no_drivers_leaves_weights_unchanged(self):
        """PASS has no positive net on any resource → weights unchanged."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        before = player.private.config.resource_weights.model_copy()
        scored = score_action(PassActionState(), player)
        update_resource_weights(player, [scored])
        assert player.private.config.resource_weights == before

    def test_basic_play_mutates_weights(self):
        """basic_play updates weights after selecting actions."""
        player = Player().build(
            money=3000, seeds={"WHEAT": 5}, method="BASIC",
        )
        before = player.private.config.resource_weights.model_copy()
        player.basic_play()
        # Weights should have been mutated (at least one field changed).
        assert player.private.config.resource_weights != before