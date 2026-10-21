import simpy


class Logger:
    def __init__(self, env: simpy.Environment, tag: str, verbose=0) -> None:
        self.env = env
        self.verbose = verbose
        self.tag = tag
        self.tables = {}

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