from src.models.game import RealityState
from src.models.environment import StepState


class Player(RealityState):
    def play(self) -> StepState:
        return StepState()