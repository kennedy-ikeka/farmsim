import simpy

class Entity:
    def __init__(self, env: simpy.Environment, tag: str, verbose: bool = False):
        self.env = env
        self.tag = tag
        self.verbose = verbose

    def log(self, message: str):
        if self.verbose:
            print(f"[{self.env.now}] {self.tag}: {message}")

    def run(self, until):
        """Run the entity"""
        self.env.run(until=until)            