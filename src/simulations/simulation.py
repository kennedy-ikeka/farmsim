from datetime import datetime

import simpy
import numpy as np

from models.farm import FarmingModel
from models.simulation import SimulationModel
from simulations.farm import Farm


class Simulation(SimulationModel):
    def __init__(self, env: simpy.Environment, farms: dict[str, FarmingModel] = {}, seed=0) -> None:
        super().__init__(env, "simulation", 3)

        self.env = env
        self.entitles = {}
        self.seed = seed
        self.timestamp = datetime.now()

        for name, farming_model in farms.items():
            self.spawn_farm(name, farming_model)

    def run(self, until):
        """Run the simulation"""
        self.env.run(until=until)   

    def load(self, path: str):
        ...

    def save(self, path: str):
        ...

    def spawn_farm(self, name: str, farming_model = FarmingModel()):
        self.info("Spawning Farm")
        Farm(self, name=name, farming_model=farming_model)