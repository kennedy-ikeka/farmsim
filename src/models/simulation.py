from datetime import datetime

from pydantic import Field

from src.models.entity import Entity

class SimulationModel(Entity):
    assets: dict[str, dict] = Field(default_factory=dict, description="The simulation assets")
    timestamp: datetime = Field(default=datetime.now(), description="The time the simulation started")
    seed: int = Field(default=0, description="The simulation seed")
    kind: str = Field(default="Simulation")

    def load(self, path: str):
        ...

    def save(self, path: str):
        ...
