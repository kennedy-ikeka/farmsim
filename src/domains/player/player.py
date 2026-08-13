from typing import get_args

from src.domains.farm.move import get_valid_move_actions_for
from src.models.action import ActionState, PassActionState
from src.models.game import RealityState
from src.models.environment import StepState


class Player(RealityState):
    def get_valid_pass_actions(self):
        return [PassActionState()]


    def get_valid_actions(self) -> list[ActionState]:
        actions: list[ActionState] = []
        actions.extend(self.get_valid_pass_actions())
        farm = self.farms[self.player]
        actions.extend(get_valid_move_actions_for(farm, farm.farmer))
        for hand_pos in farm.hands:
            actions.extend(get_valid_move_actions_for(farm, hand_pos))
        return actions

    def play(self) -> StepState:
        actions = self.get_valid_actions()

        return StepState()