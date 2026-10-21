import simpy
import numpy as np
import pandas as pd
from datetime import datetime
from os import makedirs

from models.simulation import SimulationModel
from utils.logger import Logger

class Entity(Logger):
    def __init__(self, sim: SimulationModel, type: str, id: int, verbose: int = 0, active=True):
        super().__init__(sim.env, f"{type}_{id}", verbose=verbose)
        self.sim = sim
        self.type = type
        self.id = id
        
        np.random.seed(self.sim.seed)
        self.rng = np.random

        self.tables = {}
        self.active = active
        self.start_time = self.env.now

        self.plug_in()

    def plug_in(self):
        type_entities: list = self.sim.entitles.get(self.type, [])
        type_entities.append(self)
        self.sim.entitles[self.type] = type_entities

    def run(self, until):
        """Run the entity"""
        if not self.active:
            return

        self.env.run(until=until)   

    def get_frame(self, domain: str):
        table = self.tables.get(domain, None)
        if not table:
            return None
        
        return pd.DataFrame(table)

    def get_age(self):
        return int(self.env.now - self.start_time)

    def save(self):        
        now = self.sim.timestamp.strftime("%d_%m_%Y_%H_%M_%S")
        path = f'../data/simulations_{now}'
        makedirs(path, exist_ok=True)

        for table in self.tables.keys():
            frame = self.get_frame(table)
            if frame is None:
                continue
            frame.to_csv(f"{path}/{self.tag}_{table}.csv")