from datetime import datetime

import simpy

from utils.logger import Logger


class SimulationModel(Logger):
    env: simpy.Environment
    entitles: dict
    timestamp: datetime
    seed: int
    

    def load(self, path: str):
        ...

    def save(self, path: str):
        ...
