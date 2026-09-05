import simpy

class Entity:
    def __init__(self, env: simpy.Environment, name: str, verbose: bool = True):
        self.env = env
        self.name = name
        self.verbose = verbose

    def log(self, message: str):
        if self.verbose:
            print(f"[{self.env.now}] {self.name}: {message}")
            