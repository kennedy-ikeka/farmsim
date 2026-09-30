import simpy
import numpy as np

class Entity:
    def __init__(self, env: simpy.Environment, tag: str, verbose: bool = False, seed=0):
        self.env = env
        self.tag = tag
        self.verbose = verbose

        np.random.seed(seed)
        self.rng = np.random

        self.tables = {}

    def log(self, message: str):
        if self.verbose:
            print(f"[{self.env.now}] {self.tag}: {message}")

    def run(self, until):
        """Run the entity"""
        self.env.run(until=until)            

    def metric(self, action: str, data: dict):
        table = self.tables.get(action, None)
        if not table:
            self.tables[action] = []
            table = self.tables[action]

        table.append({"time": self.env.now, "tag": self.tag, **data})
        if self.verbose:
            print(f"[{self.env.now}] {self.tag}: {action}: {data}")