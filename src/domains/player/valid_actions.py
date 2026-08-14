"""Valid action aggregation — moved from Player class into standalone functions.

All functions take a `player` (a RealityState-shaped object) as first arg.
Player methods delegate here; module-level aliases in player.py re-export these.
"""
from src.domains.farm.move import get_valid_move_actions_for
from src.domains.farm.plant import get_valid_plant_actions_for
from src.domains.farm.water import get_valid_water_actions_for
from src.domains.farm.harvest import get_valid_harvest_actions_for
from src.domains.farm.fertilize import get_valid_fertilize_actions_for
from src.domains.farm.dig import get_valid_dig_actions_for
from src.domains.farm.build_structure import get_valid_build_actions_for
from src.domains.farm.feed import get_valid_feed_actions_for
from src.domains.farm.collect_fertilizer import get_valid_collect_fertilizer_actions_for
from src.domains.farm.care import get_valid_care_actions_for
from src.domains.farm.pickup import get_valid_pickup_actions_for
from src.domains.farm.place import get_valid_place_actions_for
from src.domains.market.buy_seed import get_valid_buy_seed_actions
from src.domains.market.buy_product import get_valid_buy_product_actions
from src.domains.market.buy_animal import get_valid_buy_animal_actions
from src.domains.market.sell import get_valid_sell_actions
from src.domains.market.hire import get_valid_hire_actions
from src.domains.market.buy_land import get_valid_buy_land_actions
from src.models.action import ActionState, PassActionState
from src.models.environment import ValidStepsState
from src.models.game import RealityState


def get_valid_pass_actions() -> list[PassActionState]:
    return [PassActionState()]


def get_valid_farm_actions_for(player: RealityState, unit_pos: list[int], inv_index: int) -> list[ActionState]:
    """All valid farm actions for a single unit at `unit_pos`."""
    actions: list = []
    farm = player.farms[player.player]
    actions.extend(get_valid_move_actions_for(farm, unit_pos))
    actions.extend(get_valid_plant_actions_for(player, unit_pos))
    actions.extend(get_valid_water_actions_for(farm, unit_pos))
    actions.extend(get_valid_harvest_actions_for(player, unit_pos))
    actions.extend(get_valid_fertilize_actions_for(player, unit_pos))
    actions.extend(get_valid_dig_actions_for(farm, unit_pos))
    actions.extend(get_valid_build_actions_for(farm, unit_pos))
    actions.extend(get_valid_feed_actions_for(player, unit_pos))
    actions.extend(get_valid_collect_fertilizer_actions_for(farm, unit_pos))
    actions.extend(get_valid_care_actions_for(farm, unit_pos))
    actions.extend(get_valid_pickup_actions_for(player, unit_pos, inv_index))
    actions.extend(get_valid_place_actions_for(player, unit_pos, inv_index))
    return actions


def get_valid_market_actions(player: RealityState) -> list[ActionState]:
    """All valid market actions for `player`."""
    actions: list = []
    actions.extend(get_valid_buy_seed_actions(player))
    actions.extend(get_valid_buy_product_actions(player))
    actions.extend(get_valid_buy_animal_actions(player))
    actions.extend(get_valid_sell_actions(player))
    actions.extend(get_valid_hire_actions(player))
    actions.extend(get_valid_buy_land_actions(player))
    return actions


def get_valid_actions(player: RealityState) -> ValidStepsState:
    """Build the full ValidStepsState for `player` — farmer + hands + market."""
    farm = player.farms[player.player]
    farmer = list(get_valid_pass_actions())
    farmer.extend(get_valid_farm_actions_for(player, farm.farmer, 0))

    hands: list[list[ActionState]] = []
    for h, hand_pos in enumerate(farm.hands):
        hands.append(get_valid_farm_actions_for(player, hand_pos, h + 1))

    market = get_valid_market_actions(player)
    return ValidStepsState(farmer=farmer, hands=hands, market=market)