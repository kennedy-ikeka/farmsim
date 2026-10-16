import simpy
import numpy as np
import pandas as pd

class Entity:
    def __init__(self, env: simpy.Environment, type: str, id: int, verbose: int = 0, seed=0, active=True):
        self.env = env
        self.type = type
        self.id = id
        self.tag = f"{self.type}_{self.id}"
        self.verbose = verbose
        self.seed = seed
        
        np.random.seed(seed)
        self.rng = np.random

        self.tables = {}
        self.active = active
        self.start_time = self.env.now

    def error(self, message):
        if self.verbose >= 1:
            print(f"[Error] [{self.env.now}] {self.tag}: {message}")  

    def info(self, message: str):
        if self.verbose >= 2:
            print(f"[Info] [{self.env.now}] {self.tag}: {message}")    

    def metric(self, domain: str, data: dict):
        table = self.tables.get(domain, None)
        if not table:
            self.tables[domain] = []
            table = self.tables[domain]

        table.append({"time": self.env.now, "tag": self.tag, **data})
        if self.verbose >= 3:
            print(f"[Metric] [{self.env.now}] {self.tag}: {domain}: {data}")  

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
    