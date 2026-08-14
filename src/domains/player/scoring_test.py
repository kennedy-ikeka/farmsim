"""Tests for action scoring — cost / reward / risk / final score."""
from src.domains.player.player import Player
from src.domains.player.valid_actions import get_valid_actions
from src.domains.player.scoring import (
    available_resources,
    action_resource_usage,
    cost_score,
    reward_score,
    risk_score,
    score_action,
    score_valid_actions,
)
from src.models.action import (
    BuyAnimalActionState,
    BuyLandActionState,
    BuySeedActionState,
    MoveActionState,
    PassActionState,
    PlantActionState,
    BuildCoopActionState,
    HireActionState,
)
from src.models.farm import AnimalState, PlantState
from src.models.resource_weights import ResourceWeights
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

    def test_plant_uses_one_seed(self):
        player = Player().build(seeds={"WHEAT": 5})
        usage = action_resource_usage(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert usage["SEED"] == 1.0
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


class TestCostScore:
    def test_pass_cost_is_step_fraction(self):
        """PASS uses 1 step; cost = (1 / EPISODE_STEPS) * step_weight."""
        player = Player().build()
        cost = cost_score(PassActionState(), player)
        expected = (1.0 / EPISODE_STEPS) * player.private.config.resource_weights.STEP
        assert abs(cost - expected) < 1e-9

    def test_plant_cost_includes_seed_scarcity(self):
        """PLANT uses 1 seed + 1 step; scarcer seeds = higher cost.

        SEED availability is valued economically: 5 WHEAT seeds = 5*10 = 50.
        usage SEED = 1 (raw count), so seed cost = (1/50) * WEIGHT.
        """
        player = Player().build(seeds={"WHEAT": 5})
        cost = cost_score(PlantActionState(type="PLANT", crop="WHEAT"), player)
        seed_cost = (1.0 / 50.0) * player.private.config.resource_weights.SEED
        step_cost = (1.0 / EPISODE_STEPS) * player.private.config.resource_weights.STEP
        assert abs(cost - (seed_cost + step_cost)) < 1e-9

    def test_buy_seed_cost_proportional_to_price(self):
        """BUY_SEED WHEAT costs 10; with 3000 money → (10/3000) * weight + step."""
        player = Player().build(money=3000)
        cost = cost_score(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=1), player)
        money_cost = (10.0 / 3000.0) * player.private.config.resource_weights.MONEY
        step_cost = (1.0 / EPISODE_STEPS) * player.private.config.resource_weights.STEP
        assert abs(cost - (money_cost + step_cost)) < 1e-9

    def test_build_cost_includes_land_scarcity(self):
        """BUILD_COOP uses 1 land; with 100 empty tiles → (1/100) * weight + step."""
        player = Player().build()
        cost = cost_score(BuildCoopActionState(type="BUILD_COOP"), player)
        land_cost = (1.0 / 100.0) * player.private.config.resource_weights.LAND
        step_cost = (1.0 / EPISODE_STEPS) * player.private.config.resource_weights.STEP
        assert abs(cost - (land_cost + step_cost)) < 1e-9

    def test_custom_weights_change_cost(self):
        """Overriding a weight on the state biases the cost score.

        PLANT WHEAT consumes 1 step; bumping STEP weight from 1.0 to 5.0
        makes the step term (and thus the total cost) ~5x larger.
        """
        player = Player().build(seeds={"WHEAT": 5})
        heavy = Player().build(
            seeds={"WHEAT": 5},
            resource_weights=ResourceWeights(STEP=5.0),
        )
        base = cost_score(PlantActionState(type="PLANT", crop="WHEAT"), player)
        bumped = cost_score(PlantActionState(type="PLANT", crop="WHEAT"), heavy)
        # The non-step term (seed) is unchanged; only the step term scales by 5.
        seed_term = (1.0 / 50.0) * player.private.config.resource_weights.SEED
        step_term_base = (1.0 / EPISODE_STEPS) * 1.0
        step_term_heavy = (1.0 / EPISODE_STEPS) * 5.0
        assert abs(base - (seed_term + step_term_base)) < 1e-9
        assert abs(bumped - (seed_term + step_term_heavy)) < 1e-9
        assert bumped > base


class TestScoreAction:
    def test_final_score_is_negative_half_cost(self):
        """With reward=0 and risk=0: score = 0 - (cost + 0) / 2 = -cost/2."""
        player = Player().build(seeds={"WHEAT": 5})
        scored = score_action(PlantActionState(type="PLANT", crop="WHEAT"), player)
        assert abs(scored.score - (-scored.cost_score / 2)) < 1e-9
        assert scored.reward_score == 0.0
        assert scored.risk_score == 0.0

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

    def test_all_scored_actions_have_negative_scores(self):
        """With only cost (reward=0), all final scores should be negative."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        scored = score_valid_actions(get_valid_actions(player), player)
        for s in scored.farmer + scored.market:
            assert s.score <= 0.0

    def test_smoke_test_with_rich_player(self):
        """A rich player with seeds gets scored actions including BUY_SEED and PLANT."""
        player = Player().build(money=3000, seeds={"WHEAT": 5})
        scored = score_valid_actions(get_valid_actions(player), player)
        farmer_types = {s.action.type for s in scored.farmer}
        market_types = {s.action.type for s in scored.market}
        assert "PASS" in farmer_types
        assert "PLANT" in farmer_types
        assert "BUY_SEED" in market_types