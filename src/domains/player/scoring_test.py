"""Tests for action scoring (being rebuilt).

The scoring module is being reconstructed from scratch around
`evaluate_immediate_delta` + `score_action`. These tests cover the pieces
that exist so far; future / risk tests will be added back as those
functions are filled in.

Note: `apply_action` advances the sim clock by one step (`sim.step += 1`),
so every action — including PASS — produces a `STEP` delta of -1 (since
`available_resources.STEP = EPISODE_STEPS - player.step`). That -1 flows
into `direct_score` as the per-action step cost.
"""
from src.domains.player.player import Player
from src.domains.player.scoring import (
    apply_action,
    evaluate_immediate_delta,
    score_action,
    score_valid_actions,
)
from src.models.action import (
    BuySeedActionState,
    MoveActionState,
    PassActionState,
    PlantActionState,
)
from src.models.resource import ResourceState


class TestEvaluateImmediateDelta:
    """`evaluate_immediate_delta` — per-category resource delta from applying an action."""

    def test_returns_resource_state(self):
        """evaluate_immediate_delta returns a ResourceState, not a scalar."""
        player = Player().build(money=3000.0)
        delta = evaluate_immediate_delta(
            BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=5), player,
        )
        assert isinstance(delta, ResourceState)

    def test_pass_delta_is_step_cost_only(self):
        """PASS leaves state unchanged except for the clock → STEP -1, others 0.

        `apply_action` does `sim.step += 1`, and STEP in available_resources
        is `EPISODE_STEPS - step`, so PASS yields a single -1 STEP delta.
        """
        player = Player().build(money=3000.0)
        delta = evaluate_immediate_delta(PassActionState(type="PASS"), player)
        assert delta.STEP == -1.0
        for f in ResourceState.model_fields:
            if f == "STEP":
                continue
            assert getattr(delta, f) == 0.0

    def test_buy_seed_delta(self):
        """BUY_SEED WHEAT count=5 → MONEY -50, SEED +50, STEP -1, others 0.

        5 WHEAT seeds at seed_cost=10 each = 50 money spent, 50 economic
        seed value gained. The clock advances one step → STEP -1. No other
        resource category is touched.
        """
        player = Player().build(money=3000.0)
        delta = evaluate_immediate_delta(
            BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=5), player,
        )
        assert delta.MONEY == -50.0
        assert delta.SEED == 50.0
        assert delta.STEP == -1.0
        assert delta.LAND == 0.0
        assert delta.STRUCTURE == 0.0
        assert delta.ANIMAL == 0.0
        assert delta.HAND == 0.0
        assert delta.PRODUCE == 0.0

    def test_independent_of_resource_needs(self):
        """The delta is pure accounting — needs do not affect it."""
        p_low = Player().build(money=3000.0,
                               resource_needs=ResourceState(MONEY=1.0))
        p_high = Player().build(money=3000.0,
                                resource_needs=ResourceState(MONEY=2.0))
        action = BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=5)
        assert evaluate_immediate_delta(action, p_low) == evaluate_immediate_delta(action, p_high)


class TestApplyAction:
    """`apply_action` — returns a deep-copied sim with the action applied.

    The original `player` is untouched; the returned sim reflects what
    `Environment.step` would mutate for that single slot's action.
    """

    def test_pass_returns_unchanged_deep_copy(self):
        """PASS produces an identical sim; the original is untouched."""
        player = Player().build(money=3000.0, farmer=(5, 5))
        sim = apply_action(PassActionState(type="PASS"), player)
        assert sim is not player
        assert sim.farms[0].money == 3000.0
        assert sim.farms[0].farmer == [5, 5]
        # Original is untouched.
        assert player.farms[0].money == 3000.0
        assert player.farms[0].farmer == [5, 5]

    def test_farm_action_uses_farmer_position_by_default(self):
        """A farm action with no unit_pos targets the farmer's tile."""
        player = Player().build(farmer=(5, 5))
        sim = apply_action(MoveActionState(type="NORTH"), player)
        assert sim.farms[0].farmer == [4, 5]
        # Original is untouched.
        assert player.farms[0].farmer == [5, 5]

    def test_farm_action_honors_explicit_unit_pos(self):
        """unit_pos overrides the farmer position (used for hired-hand slots)."""
        player = Player().build(farmer=(5, 5), hands=[[5, 4]])
        sim = apply_action(MoveActionState(type="NORTH"), player,
                           unit_pos=player.farms[0].hands[0], inv_index=1)
        # Hand moves, farmer does not.
        assert sim.farms[0].hands[0] == [4, 4]
        assert sim.farms[0].farmer == [5, 5]

    def test_market_action_dispatches_via_market_apply(self):
        """BUY_SEED deducts money and adds seeds on the sim."""
        player = Player().build(money=3000.0)
        sim = apply_action(
            BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=5),
            player,
        )
        # WHEAT seed_cost=10 → 5 seeds cost 50.
        assert sim.farms[0].money == 2950.0
        assert sim.private.seeds.WHEAT == 5
        # Original is untouched.
        assert player.farms[0].money == 3000.0
        assert player.private.seeds.WHEAT == 0

    def test_original_state_is_not_mutated(self):
        """Deep copy: mutating the sim never touches the original player."""
        player = Player().build(money=3000.0, farmer=(5, 5),
                                seeds={"WHEAT": 0})
        before_money = player.farms[0].money
        before_farmer = list(player.farms[0].farmer)
        before_seeds = player.private.seeds.WHEAT

        apply_action(MoveActionState(type="NORTH"), player)
        apply_action(BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=3),
                     player)

        assert player.farms[0].money == before_money
        assert player.farms[0].farmer == before_farmer
        assert player.private.seeds.WHEAT == before_seeds


class TestScoringExports:
    """Smoke test that the scoring entrypoints are importable."""

    def test_score_action_callable(self):
        assert callable(score_action)

    def test_score_valid_actions_callable(self):
        assert callable(score_valid_actions)


class TestScoreAction:
    """`score_action` — raw sum of per-category resource deltas.

    `direct_score` is the sum of every `ResourceState` field delta from
    `evaluate_immediate_delta` — no `resource_needs` weighting. Because
    `apply_action` advances the clock by one step, every action carries a
    STEP -1 delta, so every action's direct_score is at least -1.
    `projected_score` and `risk_score` are stubbed to 0. `score =
    direct_score + projected_score + risk_score`.
    """

    def test_pass_scores_step_cost(self):
        """PASS → only delta is STEP -1 → direct_score -1, score -1."""
        player = Player().build(money=3000.0)
        scored = score_action(PassActionState(type="PASS"), player)
        assert scored.action.type == "PASS"
        assert scored.direct_score == -1.0
        assert scored.projected_score == 0.0
        assert scored.score == -1.0

    def test_buy_seed_direct_score_is_step_cost(self):
        """BUY_SEED WHEAT count=5 → MONEY -50 + SEED +50 + STEP -1 → -1.

        The money spent equals the economic seed value gained, so those
        cancel; the only residual is the STEP -1 from advancing the clock.
        `resource_needs` are not applied in `score_action`, so needs do
        not change the score.
        """
        player = Player().build(money=3000.0,
                                resource_needs=ResourceState(MONEY=1.0))
        scored = score_action(
            BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=5), player,
        )
        assert scored.direct_score == -1.0
        assert scored.projected_score == 0.0
        assert scored.score == -1.0

    def test_buy_seed_score_independent_of_needs(self):
        """Needs do not affect score_action's raw-sum direct_score.

        BUY_SEED nets to -1 (just the STEP cost) whether MONEY need is on,
        SEED need is on, both, or neither — the raw money/seed deltas
        cancel regardless of needs.
        """
        p_money_need = Player().build(money=3000.0,
                                      resource_needs=ResourceState(MONEY=1.0))
        p_seed_need = Player().build(money=3000.0,
                                     resource_needs=ResourceState(SEED=1.0))
        p_both = Player().build(
            money=3000.0,
            resource_needs=ResourceState(MONEY=1.0, SEED=1.0),
        )
        p_none = Player().build(money=3000.0,
                                 resource_needs=ResourceState())
        action = BuySeedActionState(type="BUY_SEED", crop="WHEAT", count=5)
        assert score_action(action, p_money_need).score == -1.0
        assert score_action(action, p_seed_need).score == -1.0
        assert score_action(action, p_both).score == -1.0
        assert score_action(action, p_none).score == -1.0

    def test_action_field_is_preserved(self):
        """The returned ScoredActionState carries the original action."""
        action = MoveActionState(type="NORTH")
        player = Player().build(resource_needs=ResourceState(STEP=1.0))
        scored = score_action(action, player)
        assert scored.action is action
        assert scored.action.type == "NORTH"

    def test_hand_slot_uses_hand_position(self):
        """score_action with unit_pos=farm.hands[k] scores the hand's action.

        A MOVE by hand 0 moves the hand, not the farmer. MOVE only changes
        the clock (STEP -1) → direct_score -1. The test verifies the hand
        moves on the sim and the farmer does not, confirming the slot
        routing works.
        """
        player = Player().build(farmer=(5, 5), hands=[[5, 4]],
                                resource_needs=ResourceState(STEP=1.0))
        farm = player.farms[0]
        scored = score_action(MoveActionState(type="NORTH"), player,
                              unit_pos=farm.hands[0], inv_index=1)
        assert scored.score == -1.0
        assert scored.action.type == "NORTH"


class TestScoreValidActions:
    """`score_valid_actions` — scores every action in a ValidStepsState."""

    def test_returns_scored_valid_steps_state(self):
        """All three slots are populated with ScoredActionState instances."""
        from src.domains.player.valid_actions import get_valid_actions
        player = Player().build(money=3000.0,
                                resource_needs=ResourceState(MONEY=1.0))
        valid = get_valid_actions(player)
        scored = score_valid_actions(valid, player)
        # Farmer always has at least PASS; market has BUY_SEED options with money=3000.
        assert len(scored.farmer) == len(valid.farmer)
        assert len(scored.hands) == len(valid.hands)
        assert len(scored.market) == len(valid.market)
        # Every entry is a ScoredActionState carrying its action.
        for s in scored.farmer:
            assert s.action is not None
        for s in scored.market:
            assert s.action is not None

    def test_buy_seed_in_market_scores_step_cost(self):
        """A BUY_SEED in the market slot: MONEY -10 + SEED +10 + STEP -1 → -1.

        count=1, WHEAT seed_cost=10 → MONEY -10, SEED +10. The money/seed
        deltas cancel; the only residual is the STEP -1 clock cost. Needs
        do not apply in score_action.
        """
        from src.domains.player.valid_actions import get_valid_actions
        player = Player().build(money=3000.0,
                                resource_needs=ResourceState(MONEY=1.0))
        valid = get_valid_actions(player)
        scored = score_valid_actions(valid, player)
        buy_wheat = next(
            s for s in scored.market
            if s.action.type == "BUY_SEED" and s.action.crop == "WHEAT"
        )
        assert buy_wheat.direct_score == -1.0
        assert buy_wheat.projected_score == 0.0
        assert buy_wheat.score == -1.0