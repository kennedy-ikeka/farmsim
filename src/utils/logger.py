from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field
from simpy.core import Environment

class Logger(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    env: Environment = Field(default_factory=Environment, description="The simulation environment")
    kind: str = Field(..., description="The kind of entity")
    id: str = Field(default_factory=lambda: uuid4().hex, description="The id of the entity")
    verbose: int = Field(default=0, description="The log level", ge=0, le=3)
    tables: dict[str, list[dict]] = Field(default_factory=dict, description="The tables for the entity")

    @computed_field
    @property
    def tag(self) -> str:
        return f"{self.kind}_{self.id}"

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